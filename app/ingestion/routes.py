"""Ingestion routes — file upload and dataset management."""

import os
import json
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify, g
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import ingestion_bp
from .cleaner import parse_and_clean
from ..extensions import db
from ..models.dataset import Dataset
from ..models.sales import SalesRecord
from ..models.customer import Customer
from app.auth.decorators import require_supabase_auth


ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@ingestion_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Validate file presence
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not _allowed_file(file.filename):
            flash('Only CSV and XLSX files are supported.', 'danger')
            return redirect(request.url)

        industry_type = request.form.get('industry_type', 'generic')
        filename = secure_filename(file.filename)
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, f"{current_user.id}_{filename}")
        file.save(filepath)

        try:
            df, cleaning_report = parse_and_clean(filepath, industry_type)
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            os.remove(filepath)
            return redirect(request.url)

        if df.empty:
            flash('File contained no usable data rows after cleaning.', 'warning')
            os.remove(filepath)
            return redirect(request.url)

        # Upload original file to Supabase Storage if configured
        from app.supabase_config import supabase
        if supabase is not None:
            try:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                storage_path = f"{current_user.id}/{filename}"
                supabase.storage.from_("datasets").upload(
                    path=storage_path,
                    file=file_data,
                    file_options={"x-upsert": "true"}
                )
            except Exception as e:
                current_app.logger.error(f"Failed to upload raw file to Supabase Storage: {e}")

        # Create dataset record
        dataset = Dataset(
            user_id=current_user.id,
            original_filename=filename,
            row_count=len(df),
            status='processing',
            industry_type=industry_type,
            cleaning_report=json.dumps(cleaning_report),
        )
        db.session.add(dataset)
        db.session.flush()  # get dataset.id

        # Bulk insert sales records
        records = []
        for _, row in df.iterrows():
            record = SalesRecord(
                dataset_id=dataset.id,
                date=row.get('date'),
                product=row.get('product'),
                category=row.get('category'),
                quantity=row.get('quantity'),
                unit_price=row.get('unit_price'),
                revenue=row.get('revenue'),
                region=row.get('region'),
                customer_id=str(row.get('customer_id', '')),
                cost=row.get('cost'),
            )
            records.append(record)

        db.session.add_all(records)

        # Extract unique customers
        if 'customer_id' in df.columns:
            customer_groups = df.groupby('customer_id')['date'].agg(['min', 'max']).reset_index()
            for _, cg in customer_groups.iterrows():
                cust_id_val = str(cg['customer_id'])
                if cust_id_val and cust_id_val != 'anonymous':
                    customer = Customer(
                        dataset_id=dataset.id,
                        customer_external_id=cust_id_val,
                        first_seen=cg['min'],
                        last_seen=cg['max'],
                    )
                    db.session.add(customer)

        dataset.status = 'ready'
        db.session.commit()

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except OSError:
            pass

        flash(
            f'Dataset uploaded successfully! {cleaning_report["final_rows"]} rows processed. '
            f'{cleaning_report["duplicates_removed"]} duplicates removed.',
            'success'
        )
        return redirect(url_for('ingestion.dataset_detail', dataset_id=dataset.id))

    # GET — show upload form + list existing datasets
    datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(
        Dataset.uploaded_at.desc()
    ).all()
    return render_template('upload.html', datasets=datasets)


@ingestion_bp.route('/<int:dataset_id>')
@login_required
def dataset_detail(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('ingestion.upload'))

    cleaning_report = json.loads(dataset.cleaning_report) if dataset.cleaning_report else {}
    sample_records = SalesRecord.query.filter_by(dataset_id=dataset.id).limit(25).all()

    return render_template('dataset_detail.html',
                           dataset=dataset,
                           cleaning_report=cleaning_report,
                           sample_records=sample_records)


@ingestion_bp.route('/api/list', methods=['GET'])
@require_supabase_auth
def api_list_datasets():
    datasets = Dataset.query.filter_by(user_id=g.user.id).order_by(
        Dataset.uploaded_at.desc()
    ).all()
    return jsonify([{
        'id': d.id,
        'original_filename': d.original_filename,
        'row_count': d.row_count,
        'status': d.status,
        'industry_type': d.industry_type,
        'uploaded_at': d.uploaded_at.isoformat()
    } for d in datasets])


@ingestion_bp.route('/api/upload', methods=['POST'])
@require_supabase_auth
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Only CSV and XLSX files are supported.'}), 400

    industry_type = request.form.get('industry_type', 'generic')
    filename = secure_filename(file.filename)
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, f"{g.user.id}_{filename}")
    file.save(filepath)

    try:
        df, cleaning_report = parse_and_clean(filepath, industry_type)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400

    if df.empty:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'File contained no usable data rows after cleaning.'}), 400

    # Upload original file to Supabase Storage if configured
    from app.supabase_config import supabase
    if supabase is not None:
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
            storage_path = f"{g.user.id}/{filename}"
            supabase.storage.from_("datasets").upload(
                path=storage_path,
                file=file_data,
                file_options={"x-upsert": "true"}
            )
        except Exception as e:
            current_app.logger.error(f"Failed to upload raw file to Supabase Storage: {e}")

    # Create dataset record
    dataset = Dataset(
        user_id=g.user.id,
        original_filename=filename,
        row_count=len(df),
        status='processing',
        industry_type=industry_type,
        cleaning_report=json.dumps(cleaning_report),
    )
    db.session.add(dataset)
    db.session.flush()

    # Bulk insert sales records
    records = []
    for _, row in df.iterrows():
        record = SalesRecord(
            dataset_id=dataset.id,
            date=row.get('date'),
            product=row.get('product'),
            category=row.get('category'),
            quantity=row.get('quantity'),
            unit_price=row.get('unit_price'),
            revenue=row.get('revenue'),
            region=row.get('region'),
            customer_id=str(row.get('customer_id', '')),
            cost=row.get('cost'),
        )
        records.append(record)

    db.session.add_all(records)

    # Extract unique customers
    if 'customer_id' in df.columns:
        customer_groups = df.groupby('customer_id')['date'].agg(['min', 'max']).reset_index()
        for _, cg in customer_groups.iterrows():
            cust_id_val = str(cg['customer_id'])
            if cust_id_val and cust_id_val != 'anonymous':
                customer = Customer(
                    dataset_id=dataset.id,
                    customer_external_id=cust_id_val,
                    first_seen=cg['min'],
                    last_seen=cg['max'],
                )
                db.session.add(customer)

    dataset.status = 'ready'
    db.session.commit()

    # Clean up uploaded file
    try:
        os.remove(filepath)
    except OSError:
        pass

    return jsonify({
        'message': 'Dataset uploaded successfully!',
        'dataset': {
            'id': dataset.id,
            'original_filename': dataset.original_filename,
            'row_count': dataset.row_count,
            'status': dataset.status
        },
        'cleaning_report': cleaning_report
    })

