"""Customer model — deduplicated customer dimension from sales data."""

from ..extensions import db


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False, index=True)
    customer_external_id = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    first_seen = db.Column(db.Date, nullable=True)
    last_seen = db.Column(db.Date, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('dataset_id', 'customer_external_id',
                            name='uq_customer_dataset_extid'),
    )

    def __repr__(self):
        return f'<Customer {self.customer_external_id}>'
