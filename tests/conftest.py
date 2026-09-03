"""
Main pytest configuration for MAS Survey tests.
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
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end browser tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "cli: CLI tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time")


@pytest.fixture(scope='session')
def project_root_path():
    """Get project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope='session')
def test_data_dir(project_root_path):
    """Get test data directory."""
    return project_root_path / 'tests' / 'fixtures'


@pytest.fixture(scope='session')
def base_url():
    """Get base URL for tests."""
    return os.environ.get('TEST_BASE_URL', 'http://localhost:5000')


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing."""
    from app import create_app
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope='session')
def sample_points():
    """Sample survey points for testing."""
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]


@pytest.fixture(scope='function')
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture(scope='function')
def app_with_temp_db(temp_db):
    """Create Flask application with temporary database."""
    from app import create_app
    app = create_app('testing')
    app.config['DATABASE'] = temp_db
    from app.shared.models import init_db
    init_db(temp_db)
    return app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def sample_file(client):
    """Create a sample survey file via API."""
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

    try:
        client.delete(f'/api/files/{file_name}')
    except Exception:
        pass


@pytest.fixture(scope='function')
def super_admin_user(app):
    """Get or create super admin user for testing."""
    from app.shared.models import User
    db = app.config['DATABASE']
    
    # Check if super_admin exists
    user = User.get_by_username(db, 'admin')
    if not user:
        User.create(db, 'admin', 'admin123', 'super_admin', 
                   email='admin@test.com', full_name='Test Super Admin')
        user = User.get_by_username(db, 'admin')
    return user


@pytest.fixture(scope='function')
def logged_in_super_admin(client, super_admin_user):
    """Login as super_admin and return client."""
    client.post('/auth/login', json={
        'username': super_admin_user['username'], 
        'password': 'admin123'
    })
    return client


import time
import tempfile
