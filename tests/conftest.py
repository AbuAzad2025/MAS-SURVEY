"""
Main pytest configuration for MAS Survey tests.
PostgreSQL: testing uses mas_survey_test DB, schema is created once per session.
"""
import os
import sys
import pytest
import tempfile
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end browser tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "cli: CLI tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time")


@pytest.fixture(scope='session')
def project_root_path():
    return Path(__file__).parent.parent


@pytest.fixture(scope='session')
def test_data_dir(project_root_path):
    return project_root_path / 'tests' / 'fixtures'


@pytest.fixture(scope='session')
def base_url():
    return os.environ.get('TEST_BASE_URL', 'http://localhost:5000')


@pytest.fixture(scope='session')
def app():
    """Create Flask application bound to mas_survey_test PostgreSQL DB."""
    from app import create_app
    from app.shared.models import db, Tenant, User, Role, TenantUser
    from datetime import datetime, timedelta

    app = create_app('testing')

    with app.app_context():
        # Drop & recreate schema for a clean test session.
        db.drop_all()
        db.create_all()

        # Default super admin + tenant.
        admin = User(
            username='admin', email='admin@test.com',
            role=Role.SUPER_ADMIN, full_name='Test Super Admin',
            is_active=True, whatsapp_verified=True,
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()

        tenant = Tenant(
            owner_id=admin.id, name='admin', plan='enterprise',
            expires_at=datetime.utcnow() + timedelta(days=3650),
        )
        db.session.add(tenant)
        db.session.flush()
        db.session.add(TenantUser(tenant_id=tenant.id, user_id=admin.id, role='owner'))
        db.session.commit()

    yield app

    # Leave the schema in place for inspection; uncomment to drop:
    # with app.app_context():
    #     db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def app_with_temp_db(app):
    """Back-compat alias for tests that used a temp SQLite file. Now a passthrough."""
    return app


@pytest.fixture(scope='session')
def sample_points():
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]


@pytest.fixture(scope='function')
def temp_db():
    """Back-compat: was a tempfile path; now a passthrough to session DB."""
    from app import create_app
    app = create_app('testing')
    return app.config['SQLALCHEMY_DATABASE_URI']


@pytest.fixture
def db_session(app):
    """Expose the SQLAlchemy session for tests that need direct access."""
    from app.shared.models import db
    return db.session


@pytest.fixture(scope='function')
def sample_file(client, app):
    """Create a sample survey file via API."""
    from app.shared.models import db, SurveyFile
    file_name = f'test_file_{int(time.time())}'

    with client.session_transaction() as sess:
        sess['current_file'] = file_name

    client.post('/api/files', json={
        'name': file_name,
        'date': '2026-08-31',
        'place': 'Test Location'
    })

    points = [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
    ]
    client.post('/api/points', json={'points': points})

    yield {'name': file_name, 'points': points}

    with app.app_context():
        f = SurveyFile.query.filter_by(name=file_name).first()
        if f:
            db.session.delete(f)
            db.session.commit()


@pytest.fixture(scope='function')
def super_admin_user(app):
    """Get the seeded super_admin user (created once per session)."""
    from app.shared.models import User
    with app.app_context():
        return User.query.filter_by(username='admin').first().to_dict()


@pytest.fixture
def logged_in_super_admin(client, super_admin_user):
    client.post('/auth/login', json={
        'username': super_admin_user['username'],
        'password': 'admin123'
    })
    return client
