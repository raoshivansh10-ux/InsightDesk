"""Background scheduler for automated tasks."""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging

scheduler = BackgroundScheduler()

def start_scheduler(app):
    """Initializes and starts the background scheduler."""
    # Run weekly digest job every Monday at 8:00 AM
    scheduler.add_job(
        func=send_scheduled_reports,
        trigger='cron',
        day_of_week='mon',
        hour=8,
        minute=0,
        args=[app],
        id='weekly_digest_job',
        replace_existing=True
    )
    
    if not scheduler.running:
        scheduler.start()
        logging.info("Background scheduler started.")

def send_scheduled_reports(app):
    """Job to send all active weekly subscriptions."""
    from app.models.report_subscription import ReportSubscription
    from app.models.dataset import Dataset
    from app.reporting.generator import generate_and_send_weekly_digest
    from app.extensions import db
    
    with app.app_context():
        # Get all active weekly subscriptions
        subs = ReportSubscription.query.filter_by(is_active=True, frequency='weekly').all()
        count = 0
        for sub in subs:
            try:
                dataset = Dataset.query.get(sub.dataset_id)
                if dataset:
                    success = generate_and_send_weekly_digest(dataset, sub.email)
                    if success:
                        sub.last_sent_at = datetime.utcnow()
                        count += 1
            except Exception as e:
                logging.error(f"Failed to send scheduled report to {sub.email}: {e}")
                
        db.session.commit()
        logging.info(f"Scheduled reports sent successfully to {count} subscribers.")
