import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB upload limit
    UPLOAD_FOLDER = os.path.join(basedir, '..', 'uploads')

    # Celery (Phase 8)
    CELERY_ALWAYS_EAGER = True  # synchronous in dev


class DevelopmentConfig(Config):
    """Development configuration — SQLite, debug on."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, '..', 'instance', 'insightdesk_dev.db')
    )


class ProductionConfig(Config):
    """Production configuration — Postgres, debug off."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    CELERY_ALWAYS_EAGER = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # must be set


class TestingConfig(Config):
    """Testing configuration — in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
