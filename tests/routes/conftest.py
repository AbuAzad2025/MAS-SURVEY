"""
Pytest fixtures for routes tests.
"""
import time
import pytest


@pytest.fixture(scope='function')
def sample_file(client):
    """Create a sample survey file for testing."""
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
    ]
    client.post('/api/points', json={'points': points})

    yield {'name': file_name, 'points': points}

    try:
        client.delete(f'/api/files/{file_name}')
    except Exception:
        pass
