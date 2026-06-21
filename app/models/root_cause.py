"""Root Cause Report model for storing RCA decompositions."""

from datetime import datetime
from app.extensions import db

class RootCauseReport(db.Model):
    __tablename__ = 'root_cause_reports'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    anomaly_id = db.Column(db.Integer, db.ForeignKey('anomalies.id'), nullable=True)
    
    period_current = db.Column(db.String(50), nullable=False)  # e.g., date or week string
    period_baseline = db.Column(db.String(50), nullable=False) # e.g., '30-day trailing avg'
    
    metric = db.Column(db.String(50), nullable=False)
    total_delta_pct = db.Column(db.Float, nullable=False)
    
    # JSON blob holding ranked list of contributors and candidate signals
    # Example format: 
    # [
    #   {"dimension": "region", "dimension_value": "North", "delta_value": -500, "contribution_pct": 80.5},
    #   {"type": "possible_stockout", "product": "Widget A", "confidence": "heuristic"}
    # ]
    contributors_json = db.Column(db.JSON, nullable=False)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RootCauseReport {self.id} | Anomaly {self.anomaly_id}>"
