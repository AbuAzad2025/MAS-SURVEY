"""
Pytest fixtures for API tests.
"""
import os
import sys
import time
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope='session')
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
def sample_file(client):
    """Create a sample survey file for testing."""
    file_name = f'test_file_{int(time.time())}'
    
    with client.session_transaction() as sess:
        sess['current_file'] = file_name
    
    # Create file
    client.post('/api/files', json={
        'name': file_name,
        'date': '2026-08-31',
        'place': 'Test Location'
    })
    
    # Add sample points
    points = [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]
    client.post('/api/points', json={'points': points})
    
    yield {'name': file_name, 'points': points}
    
    # Cleanup
    try:
        client.delete(f'/api/files/{file_name}')
    except Exception:
        pass


@pytest.fixture
def sample_points():
    """Sample survey points."""
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]


@pytest.fixture
def sample_dtf_content():
    """Create sample DTF file content."""
    import struct
    
    header = b'SAMPLE          '
    marker = b'\xDC\x05\x00\x00'
    date_str = b'31-8-2026     '
    
    points = [
        (1000.0, 2000.0, 50.0),
        (1100.0, 2000.0, 55.0),
        (1100.0, 2100.0, 60.0),
        (1000.0, 2100.0, 58.0),
    ]
    
    data = b''
    for y, x, h in points:
        data += struct.pack('<d', y)
        data += struct.pack('<d', x)
        data += struct.pack('<d', h)
    
    return header + marker + date_str + header + data


@pytest.fixture
def sample_traverse_data():
    """Sample traverse data."""
    return [
        {
            'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0,
            'azimuth': 0.0, 'distance': 100.0,
            'delta_y': 100.0, 'delta_x': 0.0
        },
        {
            'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0,
            'azimuth': 100.0, 'distance': 100.0,
            'delta_y': 0.0, 'delta_x': 100.0
        },
        {
            'no': 3, 'y': 100.0, 'x': 100.0, 'h': 0.0,
            'azimuth': 200.0, 'distance': 100.0,
            'delta_y': -100.0, 'delta_x': 0.0
        },
        {
            'no': 4, 'y': 0.0, 'x': 100.0, 'h': 0.0,
            'azimuth': 300.0, 'distance': 100.0,
            'delta_y': 0.0, 'delta_x': -100.0
        },
    ]
