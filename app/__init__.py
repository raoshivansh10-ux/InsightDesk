"""InsightDesk — Flask application factory."""

import os
from flask import Flask
from .config import config_by_name
from .extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure instance and uploads directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so they are registered with SQLAlchemy
    from .models import user, dataset, sales, customer  # noqa: F401

    # Register blueprints
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .ingestion import ingestion_bp
    app.register_blueprint(ingestion_bp)

    from .analytics import analytics_bp
    app.register_blueprint(analytics_bp)

    # Create tables in dev (migrations preferred in prod)
    with app.app_context():
        db.create_all()

    return app
