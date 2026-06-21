from datetime import datetime
from app.extensions import db

class Forecast(db.Model):
    """Stores generated forecasting data for a dataset."""
    __tablename__ = 'forecasts'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    model_used = db.Column(db.String(50), nullable=False)  # e.g., 'exponential_smoothing'
    horizon_days = db.Column(db.Integer, default=30, nullable=False)
    
    # Store the daily forecast points, dates, and confidence intervals
    forecast_json = db.Column(db.JSON, nullable=False)
    
    # Positive/negative trend slope of the forecast, feeds into health score
    outlook_score = db.Column(db.Float, nullable=False)

    dataset = db.relationship('Dataset', backref=db.backref('forecasts', cascade='all, delete-orphan', lazy=True))

    def __repr__(self):
        return f"<Forecast(id={self.id}, dataset_id={self.dataset_id}, model={self.model_used})>"
