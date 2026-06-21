"""Dataset model — represents an uploaded file and its processing status."""

from datetime import datetime, timezone
from ..extensions import db


class Dataset(db.Model):
    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    original_filename = db.Column(db.String(512), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    row_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending | processing | ready | error
    industry_type = db.Column(db.String(100), default='generic')
    cleaning_report = db.Column(db.Text, nullable=True)  # JSON summary of cleaning steps

    # Relationships
    sales_records = db.relationship('SalesRecord', backref='dataset', lazy='dynamic',
                                    cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='dataset', lazy='dynamic',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Dataset {self.original_filename} [{self.status}]>'
