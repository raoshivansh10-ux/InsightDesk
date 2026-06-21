"""User model — authentication and account ownership."""

from datetime import datetime, timezone
from flask_login import UserMixin
from ..extensions import db, login_manager
import bcrypt


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    datasets = db.relationship('Dataset', backref='owner', lazy='dynamic',
                               cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and store a plaintext password."""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        """Verify a plaintext password against the stored hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def __repr__(self):
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
