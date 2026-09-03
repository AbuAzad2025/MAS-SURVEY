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
def db_with_file(app):
    """Initialize database with a test file (ORM, isolated tenant)."""
    import uuid
    from datetime import datetime, timedelta
    from app.shared.models import db, User, Role, Tenant, TenantUser, SurveyFile, SurveyPoint

    tag = f"dbwf_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    with app.app_context():
        u = User(username=f"u_{tag}", role=Role.REGISTERED, is_active=True)
        u.set_password("pw12345")
        db.session.add(u)
        db.session.flush()
        t = Tenant(owner_id=u.id, name=f"t_{tag}", plan="free",
                   expires_at=datetime.utcnow() + timedelta(days=3650))
        db.session.add(t)
        db.session.flush()
        db.session.add(TenantUser(tenant_id=t.id, user_id=u.id, role="owner"))
        file_name = f'test_file_{tag}'
        f = SurveyFile(tenant_id=t.id, name=file_name,
                       date='2026-08-31', place='Test Location')
        db.session.add(f)
        db.session.flush()
        points = [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
            {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        ]
        for p in points:
            db.session.add(SurveyPoint(tenant_id=t.id, file_id=f.id,
                                       point_no=p['no'], y=p['y'], x=p['x'], h=p['h']))
        f.no_of_points = len(points)
        db.session.commit()
        ids = (u.id, t.id, f.id)

    yield {'tenant_id': ids[1], 'file': file_name, 'file_id': ids[2], 'points': points}

    with app.app_context():
        for ff in SurveyFile.query.filter_by(tenant_id=ids[1]).all():
            db.session.delete(ff)
        tt = Tenant.query.get(ids[1])
        if tt:
            db.session.delete(tt)
        uu = User.query.get(ids[0])
        if uu:
            db.session.delete(uu)
        db.session.commit()


@pytest.fixture(autouse=True)
def login_for_protected_pages(client, super_admin_user):
    """MAS pages require login - authenticate automatically."""
    client.post('/auth/login', json={
        'username': super_admin_user['username'],
        'password': 'admin123'
    })
    return client


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
