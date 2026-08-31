"""
Integration test fixtures.
"""
import os
import sys
import time
import pytest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


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
def temp_dir():
    """Create a temporary directory for file testing."""
    path = tempfile.mkdtemp()
    yield path
    try:
        shutil.rmtree(path)
    except Exception:
        pass


@pytest.fixture(scope='function')
def app():
    """Create Flask application for testing."""
    from app import create_app
    app = create_app('testing')
    return app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_with_file(temp_db):
    """Initialize database with a test file."""
    from app.shared.models import init_db, SurveyFile, SurveyPoint

    init_db(temp_db)

    file_name = f'test_file_{int(time.time())}'
    SurveyFile.create(temp_db, file_name, '2026-08-31', 'Test Location')

    points = [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
    ]
    SurveyPoint.save_batch(temp_db, file_name, points)

    yield {'db': temp_db, 'file': file_name, 'points': points}

    SurveyFile.delete(temp_db, file_name)


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
