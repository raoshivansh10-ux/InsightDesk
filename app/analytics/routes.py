"""Analytics routes — dashboard view and API endpoints."""

from flask import render_template, redirect, url_for, flash, jsonify, g
from flask_login import login_required, current_user
from . import analytics_bp
from .kpi_engine import get_kpis
from .health_score import calculate_health_score
from .anomaly_detector import detect_anomalies
from ..models.dataset import Dataset
from ..limiter import rate_limit
from app.auth.decorators import require_supabase_auth

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
    
    # Fetch or generate RCA for the most recent anomaly to display directly on dashboard
    latest_rca = None
    if anomalies:
        from ..root_cause.engine import analyze_root_cause
        latest_anomaly = anomalies[0]
        latest_rca = analyze_root_cause(dataset.id, latest_anomaly['id'])
        if latest_rca:
            latest_rca['anomaly'] = latest_anomaly

    # Fetch or generate Forecast
    from ..models.forecast import Forecast
    forecast = Forecast.query.filter_by(dataset_id=dataset.id).first()
    if not forecast:
        from ..forecasting.engine import generate_forecast
        forecast = generate_forecast(dataset.id)

    # Fetch or generate AI Recommendations
    from ..models.insight import Insight
    recommendation_insight = Insight.query.filter_by(dataset_id=dataset.id, insight_type='recommendation').order_by(Insight.generated_at.desc()).first()
    
    if recommendation_insight:
        recommendations = recommendation_insight.content_json
    else:
        from ..ai.engine import generate_recommendations
        recommendations = generate_recommendations(dataset.id)

    # Fetch subscription status
    from ..models.report_subscription import ReportSubscription
    subscription = ReportSubscription.query.filter_by(user_id=current_user.id, dataset_id=dataset.id).first()
    is_subscribed = subscription.is_active if subscription else False

    # Fetch Data Preview
    from ..models.sales import SalesRecord
    import json
    
    sample_records = SalesRecord.query.filter_by(dataset_id=dataset.id).limit(5).all()
    
    cleaning_stats = {}
    if dataset.cleaning_report:
        try:
            cleaning_stats = json.loads(dataset.cleaning_report)
        except:
            pass

    return render_template(
        'index.html',
        dataset=dataset,
        datasets=datasets,
        kpis=kpis,
        health=health,
        anomalies=anomalies,
        latest_rca=latest_rca,
        forecast=forecast,
        recommendations=recommendations,
        is_subscribed=is_subscribed,
        sample_records=sample_records,
        cleaning_stats=cleaning_stats
    )


@analytics_bp.route('/api/<int:dataset_id>/charts')
@require_supabase_auth
def chart_data(dataset_id):
    """API endpoint to fetch chart data for Chart.js."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    kpis = get_kpis(dataset.id)
    
    from ..models.forecast import Forecast
    forecast = Forecast.query.filter_by(dataset_id=dataset.id).first()
    
    return jsonify({
        'trend': kpis['chart_data'],
        'category': kpis['category_chart'],
        'forecast': forecast.forecast_json if forecast else None
    })


@analytics_bp.route('/api/<int:dataset_id>/metadata')
@require_supabase_auth
def dataset_metadata(dataset_id):
    """API endpoint to fetch complete metadata for a dataset, including KPIs, health, anomalies, recommendations, and list of all datasets for selection."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    # Calculate KPIs
    kpis = get_kpis(dataset.id)
    health = calculate_health_score(kpis['growth_pct'])
    
    # Detect Anomalies
    anomalies = detect_anomalies(dataset.id)
    
    # Fetch or generate AI Recommendations
    from ..models.insight import Insight
    recommendation_insight = Insight.query.filter_by(dataset_id=dataset.id, insight_type='recommendation').order_by(Insight.generated_at.desc()).first()
    
    if recommendation_insight:
        recommendations = recommendation_insight.content_json
    else:
        from ..ai.engine import generate_recommendations
        recommendations = generate_recommendations(dataset.id)

    # Clean up recommendations if they are in raw string format
    if isinstance(recommendations, str):
        import json
        try:
            recommendations = json.loads(recommendations)
        except:
            pass

    # Fetch other user datasets for the dropdown
    datasets = Dataset.query.filter_by(
        user_id=current_user.id, status='ready'
    ).order_by(Dataset.uploaded_at.desc()).all()

    datasets_list = [{
        'id': d.id,
        'original_filename': d.original_filename,
        'uploaded_at': d.uploaded_at.isoformat()
    } for d in datasets]

    return jsonify({
        'id': dataset.id,
        'filename': dataset.original_filename,
        'row_count': dataset.row_count,
        'industry_type': dataset.industry_type,
        'kpis': {
            'revenue': f"${kpis['total_revenue']:,.2f}",
            'revChange': f"{kpis['growth_pct']:+.1f}%",
            'healthScore': health,
            'anomaliesCount': len(anomalies),
            'orders': f"{kpis['total_orders']:,}",
            'orderChange': f"{kpis['growth_pct']/2:+.1f}%",
        },
        'anomalies': [{
            'id': a['id'],
            'date': a['date'],
            'metric': a['metric'],
            'impact': f"{a['pct_diff']:+.1f}%",
            'severity': a['severity'],
            'message': a['message']
        } for a in anomalies],
        'recommendations': [{
            'title': r.get('title', 'Recommendation'),
            'desc': r.get('desc', 'Action details'),
            'impact': r.get('impact', 'Medium'),
            'action': r.get('action', 'Learn More')
        } for r in recommendations] if isinstance(recommendations, list) else [],
        'datasets': datasets_list
    })


@analytics_bp.route('/api/forecast/<int:dataset_id>/generate', methods=['POST'])
@require_supabase_auth
@rate_limit(limit=5, period=60)
def trigger_forecast(dataset_id):
    """Manually trigger forecast generation."""
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..forecasting.engine import generate_forecast
    forecast = generate_forecast(dataset.id)
    
    if not forecast:
        return jsonify({'error': 'Not enough data to generate forecast'}), 400
        
    return jsonify({'message': 'Forecast generated', 'forecast': forecast.forecast_json})

@analytics_bp.route('/api/root-cause/<int:dataset_id>/<int:anomaly_id>')
@require_supabase_auth
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
@require_supabase_auth
@rate_limit(limit=5, period=60)
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

@analytics_bp.route('/api/ai/ask', methods=['POST'])
@require_supabase_auth
@rate_limit(limit=10, period=60)
def ask_ai():
    """Natural Language Query endpoint."""
    from flask import request
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    query = data.get('query')
    
    if not dataset_id or not query:
        return jsonify({'error': 'Missing dataset_id or query'}), 400

    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..ai.engine import answer_nlq
    answer = answer_nlq(dataset_id, query)
    
    return jsonify({'answer': answer})


@analytics_bp.route('/api/reports/subscribe', methods=['POST'])
@require_supabase_auth
def toggle_subscription():
    """Toggle email subscription for the dataset."""
    from flask import request
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..models.report_subscription import ReportSubscription
    from ..extensions import db
    
    sub = ReportSubscription.query.filter_by(user_id=current_user.id, dataset_id=dataset_id).first()
    if sub:
        sub.is_active = not sub.is_active
        db.session.commit()
        return jsonify({'message': 'Subscription updated', 'is_active': sub.is_active})
    else:
        sub = ReportSubscription(
            user_id=current_user.id,
            dataset_id=dataset_id,
            email=current_user.email,
            is_active=True
        )
        db.session.add(sub)
        db.session.commit()
        return jsonify({'message': 'Subscribed successfully', 'is_active': True})


@analytics_bp.route('/api/reports/send-now', methods=['POST'])
@require_supabase_auth
def send_report_now():
    """Immediately generate and send the report."""
    from flask import request
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    from ..reporting.generator import generate_and_send_weekly_digest
    success = generate_and_send_weekly_digest(dataset, current_user.email)
    
    if success:
        return jsonify({'message': 'Report sent successfully'})
    else:
        return jsonify({'error': 'Failed to send report. Check configuration.'}), 500
