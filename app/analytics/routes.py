"""Analytics routes — dashboard view and API endpoints."""

from flask import render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from . import analytics_bp
from .kpi_engine import get_kpis
from .health_score import calculate_health_score
from .anomaly_detector import detect_anomalies
from ..models.dataset import Dataset

@analytics_bp.route('/')
@login_required
def index():
    """Main dashboard view. Defaults to the most recent dataset."""
    # Find user's latest ready dataset
    dataset = Dataset.query.filter_by(
        user_id=current_user.id, 
        status='ready'
    ).order_by(Dataset.uploaded_at.desc()).first()

    if not dataset:
        flash('Please upload a dataset first to view the dashboard.', 'info')
        return redirect(url_for('ingestion.upload'))

    return redirect(url_for('analytics.dashboard', dataset_id=dataset.id))


@analytics_bp.route('/<int:dataset_id>')
@login_required
def dashboard(dataset_id):
    """Dashboard view for a specific dataset."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('ingestion.upload'))

    # Get other datasets for the dropdown selector
    datasets = Dataset.query.filter_by(
        user_id=current_user.id, status='ready'
    ).order_by(Dataset.uploaded_at.desc()).all()

    # Calculate KPIs
    kpis = get_kpis(dataset.id)
    health = calculate_health_score(kpis['growth_pct'])
    
    # Detect Anomalies
    anomalies = detect_anomalies(dataset.id)

    return render_template(
        'index.html',
        dataset=dataset,
        datasets=datasets,
        kpis=kpis,
        health=health,
        anomalies=anomalies
    )


@analytics_bp.route('/api/<int:dataset_id>/charts')
@login_required
def chart_data(dataset_id):
    """API endpoint to fetch chart data for Chart.js."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    kpis = get_kpis(dataset.id)
    
    return jsonify({
        'trend': kpis['chart_data'],
        'category': kpis['category_chart']
    })

@analytics_bp.route('/api/root-cause/<int:dataset_id>/<int:anomaly_id>')
@login_required
def get_root_cause(dataset_id, anomaly_id):
    """Fetch the Root Cause Analysis report for a specific anomaly."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..models.root_cause import RootCauseReport
    from ..root_cause.engine import analyze_root_cause
    
    report = RootCauseReport.query.filter_by(anomaly_id=anomaly_id, dataset_id=dataset_id).first()
    
    if not report:
        # Lazy evaluate if the report doesn't exist
        analyze_root_cause(dataset_id, anomaly_id)
        report = RootCauseReport.query.filter_by(anomaly_id=anomaly_id, dataset_id=dataset_id).first()

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    return jsonify({
        'id': report.id,
        'metric': report.metric,
        'total_delta_pct': report.total_delta_pct,
        'contributors': report.contributors_json
    })

@analytics_bp.route('/api/root-cause/<int:dataset_id>/scan', methods=['POST'])
@login_required
def trigger_rca_scan(dataset_id):
    """Manually trigger an RCA scan for recent anomalies."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..models.anomaly import Anomaly
    from ..root_cause.engine import analyze_root_cause

    # Find the most recent anomaly without a report
    anomalies = Anomaly.query.filter_by(dataset_id=dataset_id).order_by(Anomaly.detected_at.desc()).limit(5).all()
    results = []
    
    for anomaly in anomalies:
        if anomaly.severity in ['high', 'medium']:
            res = analyze_root_cause(dataset_id, anomaly.id)
            if res:
                results.append(res)
                
    return jsonify({'triggered': len(results), 'reports': results})
