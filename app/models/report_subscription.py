"""Report Subscription model."""

from datetime import datetime
from app.extensions import db

class ReportSubscription(db.Model):
    __tablename__ = 'report_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    
    email = db.Column(db.String(120), nullable=False)
    frequency = db.Column(db.String(20), default='weekly')  # 'weekly', 'daily'
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sent_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<ReportSubscription {self.email} | Dataset {self.dataset_id} | {self.frequency}>"
