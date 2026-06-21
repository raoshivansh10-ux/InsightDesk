"""Anomaly model for storing detected anomalies."""

from datetime import datetime
from app.extensions import db

class Anomaly(db.Model):
    __tablename__ = 'anomalies'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Context
    dimension = db.Column(db.String(50), nullable=True)
    dimension_value = db.Column(db.String(100), nullable=True)
    metric = db.Column(db.String(50), nullable=False)
    method = db.Column(db.String(50), nullable=False)
    
    # Values
    observed_value = db.Column(db.Float, nullable=False)
    expected_range_low = db.Column(db.Float, nullable=True)
    expected_range_high = db.Column(db.Float, nullable=True)
    
    # Flags
    severity = db.Column(db.String(20), nullable=False)  # high, medium, low
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')    # open, resolved, ignored
    
    # Type (positive/negative spike)
    type = db.Column(db.String(20), nullable=False)      # positive, negative

    def __repr__(self):
        return f"<Anomaly {self.id} | {self.metric} | {self.severity}>"
