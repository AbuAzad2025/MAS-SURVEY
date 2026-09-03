"""
Configuration settings for MAS Web Application.
PostgreSQL is the only supported DB engine.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _default_db_uri(db_name: str) -> str:
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', '123')
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}'


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mas-surveying-secret-key-2026')

    # PostgreSQL connection. Override with DATABASE_URL env var.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', _default_db_uri('mas_survey')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL', _default_db_uri('mas_survey_test')
    )


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
