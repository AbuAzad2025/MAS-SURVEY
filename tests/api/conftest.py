"""
Pytest fixtures for API tests.
PostgreSQL: session-scoped app, function-scoped client, autouse login.
"""
import os
import sys
import time
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope='session')
def app():
    from app import create_app
    from app.shared.models import db, User, Role, Tenant, TenantUser
    from datetime import datetime, timedelta

    app = create_app('testing')

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = User(
            username='admin', email='admin@test.com',
            role=Role.SUPER_ADMIN, full_name='Test Super Admin',
            is_active=True, whatsapp_verified=True,
        )
        admin.set_password('admin123')
        db.session.add(admin); db.session.flush()

        tenant = Tenant(
            owner_id=admin.id, name='admin', plan='enterprise',
            expires_at=datetime.utcnow() + timedelta(days=3650),
        )
        db.session.add(tenant); db.session.flush()
        db.session.add(TenantUser(tenant_id=tenant.id, user_id=admin.id, role='owner'))
        db.session.commit()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def login_for_protected_endpoints(client, super_admin_user):
    """All API tests assume an authenticated user. Login automatically."""
    client.post('/auth/login', json={
        'username': super_admin_user['username'],
        'password': 'admin123',
    })
    return client


@pytest.fixture
def super_admin_user(app):
    from app.shared.models import User
    with app.app_context():
        return User.query.filter_by(username='admin').first().to_dict()


@pytest.fixture(scope='function')
def sample_file(client, app):
    """Create a sample survey file with points via API."""
    from app.shared.models import db, SurveyFile
    file_name = f'test_file_{int(time.time())}'

    with client.session_transaction() as sess:
        sess['current_file'] = file_name

    client.post('/api/files', json={
        'name': file_name,
        'date': '2026-08-31',
        'place': 'Test Location',
    })

    points = [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]
    client.post('/api/points', json={'points': points})

    yield {'name': file_name, 'points': points}

    with app.app_context():
        f = SurveyFile.query.filter_by(name=file_name).first()
        if f:
            db.session.delete(f); db.session.commit()


@pytest.fixture
def sample_points():
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]


@pytest.fixture
def sample_dtf_content():
    import struct
    header = b'SAMPLE         '
    marker = b'\xDC\x05\x00\x00'
    padding = b'\x00' * 40
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
    return header + marker + padding + data


@pytest.fixture
def sample_traverse_data():
    return [
        {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'azimuth': 0.0, 'distance': 100.0,
         'delta_y': 100.0, 'delta_x': 0.0},
        {'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0, 'azimuth': 100.0, 'distance': 100.0,
         'delta_y': 0.0, 'delta_x': 100.0},
        {'no': 3, 'y': 100.0, 'x': 100.0, 'h': 0.0, 'azimuth': 200.0, 'distance': 100.0,
         'delta_y': -100.0, 'delta_x': 0.0},
        {'no': 4, 'y': 0.0, 'x': 100.0, 'h': 0.0, 'azimuth': 300.0, 'distance': 100.0,
         'delta_y': 0.0, 'delta_x': -100.0},
    ]
