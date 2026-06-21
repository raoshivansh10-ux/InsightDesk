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
