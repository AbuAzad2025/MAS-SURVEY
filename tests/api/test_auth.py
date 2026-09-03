"""
Auth API Tests for MAS Survey Application.
PostgreSQL + SQLAlchemy + tenant-scoped.
Autouse login fixture logs the user in, so the few tests that need an
unauthenticated session explicitly log out first.
"""
import time


class TestAuthLogin:
    """Test login endpoint."""

    def test_login_success(self, client, super_admin_user):
        """Test successful login with super_admin."""
        response = client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['username'] == super_admin_user['username']
        assert data['user']['role'] == 'super_admin'
        assert 'redirect' in data

    def test_login_success_registered_user(self, client, app):
        """Test successful login with a freshly-created registered user."""
        from app.shared.models import db, User, Role, Tenant, TenantUser
        from datetime import datetime, timedelta

        username = f'reg_user_{int(time.time())}'
        with app.app_context():
            u = User(username=username, email=f'{username}@test.com',
                     role=Role.REGISTERED, full_name='Registered User', is_active=True)
            u.set_password('password123')
            db.session.add(u); db.session.flush()
            t = Tenant(owner_id=u.id, name=username, plan='free',
                       expires_at=datetime.utcnow() + timedelta(days=3650))
            db.session.add(t); db.session.flush()
            db.session.add(TenantUser(tenant_id=t.id, user_id=u.id, role='owner'))
            db.session.commit()

        # Force a fresh unauthenticated client
        client.post('/auth/logout')
        response = client.post('/auth/login', json={'username': username, 'password': 'password123'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['role'] == 'registered'

    def test_login_success_guest_user(self, client, app):
        from app.shared.models import db, User, Role, Tenant, TenantUser
        from datetime import datetime, timedelta

        username = f'guest_user_{int(time.time())}'
        with app.app_context():
            u = User(username=username, email=f'{username}@test.com',
                     role=Role.GUEST, full_name='Guest User', is_active=True)
            u.set_password('password123')
            db.session.add(u); db.session.flush()
            t = Tenant(owner_id=u.id, name=username, plan='free',
                       expires_at=datetime.utcnow() + timedelta(days=3650))
            db.session.add(t); db.session.flush()
            db.session.add(TenantUser(tenant_id=t.id, user_id=u.id, role='owner'))
            db.session.commit()

        client.post('/auth/logout')
        response = client.post('/auth/login', json={'username': username, 'password': 'password123'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['role'] == 'guest'

    def test_login_invalid_username(self, client, super_admin_user):
        client.post('/auth/logout')
        response = client.post('/auth/login', json={'username': 'nonexistent_user', 'password': 'admin123'})
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_login_invalid_password(self, client, super_admin_user):
        client.post('/auth/logout')
        response = client.post('/auth/login', json={
            'username': super_admin_user['username'], 'password': 'wrong_password'
        })
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_login_missing_username(self, client):
        client.post('/auth/logout')
        response = client.post('/auth/login', json={'password': 'admin123'})
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_missing_password(self, client):
        client.post('/auth/logout')
        response = client.post('/auth/login', json={'username': 'admin'})
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_empty_credentials(self, client):
        client.post('/auth/logout')
        response = client.post('/auth/login', json={})
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_inactive_user(self, client, app):
        from app.shared.models import db, User, Role
        username = f'inactive_{int(time.time())}'
        with app.app_context():
            u = User(username=username, email=f'{username}@test.com',
                     role=Role.REGISTERED, is_active=False)
            u.set_password('password123')
            db.session.add(u); db.session.commit()

        client.post('/auth/logout')
        response = client.post('/auth/login', json={'username': username, 'password': 'password123'})
        assert response.status_code == 401


class TestAuthLogout:
    def test_logout_success(self, client, super_admin_user):
        response = client.post('/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'redirect' in data

    def test_logout_get_method(self, client, super_admin_user):
        response = client.get('/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'

    def test_logout_clears_session(self, client, super_admin_user):
        # We are already logged in via autouse. /auth/me must be 200 first.
        r = client.get('/auth/me')
        assert r.status_code == 200
        client.post('/auth/logout')
        r = client.get('/auth/me')
        assert r.status_code == 401


class TestAuthMe:
    def test_get_current_user(self, client, super_admin_user):
        response = client.get('/auth/me')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == super_admin_user['id']
        assert data['username'] == super_admin_user['username']
        assert data['role'] == 'super_admin'
        assert data['full_name'] == super_admin_user['full_name']

    def test_me_requires_login(self, client):
        client.post('/auth/logout')
        response = client.get('/auth/me')
        assert response.status_code == 401
        assert 'Authentication required' in response.get_json()['error']

    def test_me_after_logout(self, client, super_admin_user):
        client.post('/auth/logout')
        response = client.get('/auth/me')
        assert response.status_code == 401


class TestAuthChangePassword:
    def test_change_password_success(self, client, super_admin_user):
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123', 'new_password': 'new_admin123'
        })
        assert response.status_code == 200
        assert 'successfully' in response.get_json()['message']
        # Restore for the rest of the suite
        client.post('/auth/change-password', json={
            'old_password': 'new_admin123', 'new_password': 'admin123'
        })

    def test_change_password_wrong_old(self, client, super_admin_user):
        response = client.post('/auth/change-password', json={
            'old_password': 'wrong_password', 'new_password': 'new_admin123'
        })
        assert response.status_code == 400
        assert 'incorrect' in response.get_json()['error']

    def test_change_password_short_new(self, client, super_admin_user):
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123', 'new_password': '123'
        })
        assert response.status_code == 400
        assert 'at least 6 characters' in response.get_json()['error']

    def test_change_password_missing_fields(self, client, super_admin_user):
        response = client.post('/auth/change-password', json={'old_password': 'admin123'})
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_change_password_requires_login(self, client):
        client.post('/auth/logout')
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123', 'new_password': 'new_password123'
        })
        assert response.status_code == 401


class TestAuthSuperAdminInfo:
    def test_super_admin_info_endpoint(self, client):
        client.post('/auth/logout')
        response = client.get('/auth/super-admin-info')
        assert response.status_code == 200
        data = response.get_json()
        assert 'name' in data and 'whatsapp' in data and 'note' in data
        assert data['name'] == 'أبو أزاد'
        assert data['whatsapp'] == '+972562150193'


class TestAuthSessionPersistence:
    def test_session_persists_across_requests(self, client, super_admin_user):
        for _ in range(5):
            r = client.get('/auth/me')
            assert r.status_code == 200
            data = r.get_json()
            assert data['username'] == super_admin_user['username']

    def test_multiple_users_separate_sessions(self, client, app):
        from app.shared.models import db, User, Role, Tenant, TenantUser
        from datetime import datetime, timedelta

        ts = int(time.time() * 1000)
        user1 = f'user1_{ts}'
        user2 = f'user2_{ts}'
        with app.app_context():
            for username in (user1, user2):
                u = User(username=username, email=f'{username}@t.com',
                         role=Role.REGISTERED, is_active=True)
                u.set_password('pass123')
                db.session.add(u); db.session.flush()
                t = Tenant(owner_id=u.id, name=username, plan='free',
                           expires_at=datetime.utcnow() + timedelta(days=3650))
                db.session.add(t); db.session.flush()
                db.session.add(TenantUser(tenant_id=t.id, user_id=u.id, role='owner'))
            db.session.commit()

        client.post('/auth/login', json={'username': user1, 'password': 'pass123'})
        r = client.get('/auth/me')
        assert r.get_json()['username'] == user1
        client.post('/auth/login', json={'username': user2, 'password': 'pass123'})
        r = client.get('/auth/me')
        assert r.get_json()['username'] == user2
