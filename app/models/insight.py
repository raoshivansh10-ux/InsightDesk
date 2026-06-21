from datetime import datetime
from app.extensions import db

class Insight(db.Model):
    """Stores AI-generated insights, recommendations, and NLQ answers."""
    __tablename__ = 'insights'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    
    insight_type = db.Column(db.String(50), nullable=False) # e.g., 'recommendation', 'nlq_answer'
    
    # Store the text or JSON structure of the insight
    # For 'recommendation', this will be a JSON list of bullet points
    content_json = db.Column(db.JSON, nullable=False)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    dataset = db.relationship('Dataset', backref=db.backref('insights', cascade='all, delete-orphan', lazy=True))

    def __repr__(self):
        return f"<Insight(id={self.id}, dataset_id={self.dataset_id}, type={self.insight_type})>"
