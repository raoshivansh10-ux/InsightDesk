"""SalesRecord model — individual cleaned transaction rows."""

from ..extensions import db


class SalesRecord(db.Model):
    __tablename__ = 'sales_records'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    product = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    unit_price = db.Column(db.Float, nullable=True)
    revenue = db.Column(db.Float, nullable=True)  # computed: quantity * unit_price if missing
    region = db.Column(db.String(255), nullable=True)
    customer_id = db.Column(db.String(255), nullable=True)
    cost = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<SalesRecord {self.date} {self.product} ${self.revenue}>'
