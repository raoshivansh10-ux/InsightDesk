"""Report Generator."""

from flask import render_template
from .email_sender import send_email
from app.models.dataset import Dataset
from app.models.insight import Insight
from app.models.anomaly import Anomaly

def generate_and_send_weekly_digest(dataset, email):
    """
    Generates the weekly digest HTML for a given dataset and sends it.
    """
    # 1. Gather KPIs (using the existing Dataset relationships or aggregating)
    # We'll just grab the latest 5 anomalies
    recent_anomalies = Anomaly.query.filter_by(dataset_id=dataset.id).order_by(Anomaly.detected_at.desc()).limit(5).all()
    
    # Grab the latest AI Recommendation
    latest_insight = Insight.query.filter_by(dataset_id=dataset.id, insight_type='recommendation').order_by(Insight.generated_at.desc()).first()
    
    action_plan = []
    if latest_insight and latest_insight.content_json:
        # Expected format: {"recommendations": [{"title": "...", "description": "...", "impact_estimate": "..."}]}
        action_plan = latest_insight.content_json.get('recommendations', [])

    # We need to run inside a Flask app context to use render_template
    # The caller must ensure we are in an app context.
    html_content = render_template('emails/weekly_digest.html',
                                   dataset=dataset,
                                   anomalies=recent_anomalies,
                                   action_plan=action_plan)

    subject = f"InsightDesk Weekly Digest: {dataset.original_filename}"
    return send_email(subject, email, html_content)
