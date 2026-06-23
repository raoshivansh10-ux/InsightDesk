"""InsightDesk — Flask application factory."""

import os
from flask import Flask, redirect, url_for, render_template
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

    # Configure logging
    import logging
    from logging.handlers import RotatingFileHandler
    
    log_file = os.path.join(app.instance_path, 'insightdesk.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('InsightDesk startup')

    # Global DB Exception rollback guard
    from sqlalchemy.exc import SQLAlchemyError
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        db.session.rollback()
        app.logger.error(f"Database error occurred: {str(error)}")
        return render_template('errors/500.html'), 500

    # Global CORS and Security Headers
    @app.before_request
    def handle_options_request():
        from flask import request, make_response
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            return response

    @app.after_request
    def set_security_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' http://localhost:5173; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "media-src 'self' https://d8j0ntlcm91z4.cloudfront.net; "
            "connect-src 'self' http://localhost:5173 http://localhost:5000;"
        )
        return response

    # Import models so they are registered with SQLAlchemy
    from .models import user, dataset, sales, customer  # noqa: F401

    # Register blueprints
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .ingestion import ingestion_bp
    app.register_blueprint(ingestion_bp)

    from .analytics import analytics_bp
    app.register_blueprint(analytics_bp)

    from .errors import errors_bp
    app.register_blueprint(errors_bp)

    # Create tables in dev (migrations preferred in prod)
    with app.app_context():
        from .models.dataset import Dataset
        from .models.sales import SalesRecord
        from .models.customer import Customer
        from .models.anomaly import Anomaly
        from .models.root_cause import RootCauseReport
        from .models.forecast import Forecast
        from .models.insight import Insight
        from .models.report_subscription import ReportSubscription
        db.create_all()

    # Start background scheduler if not in testing/cli mode
    if not app.config.get('TESTING') and not os.environ.get('FLASK_SKIP_SCHEDULER'):
        from .scheduler import start_scheduler
        start_scheduler(app)

    @app.route('/')
    def index():
        return render_template('landing.html')

    return app
