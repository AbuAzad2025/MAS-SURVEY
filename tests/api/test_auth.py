"""
Auth API Tests for MAS Survey Application.
Tests authentication, login, logout, session management.
"""
import pytest
import json
import time
from typing import Dict, Any


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
        assert 'user' in data
        assert data['user']['username'] == super_admin_user['username']
        assert data['user']['role'] == 'super_admin'
        assert 'redirect' in data

    def test_login_success_registered_user(self, client):
        """Test successful login with registered user."""
        from app.shared.models import User
        db = client.application.config['DATABASE']
        
        # Create registered user
        username = f'reg_user_{int(time.time())}'
        User.create(db, username, 'password123', 'registered',
                   email=f'{username}@test.com', full_name='Registered User')
        
        response = client.post('/auth/login', json={
            'username': username,
            'password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['role'] == 'registered'

    def test_login_success_guest_user(self, client):
        """Test successful login with guest user."""
        from app.shared.models import User
        db = client.application.config['DATABASE']
        
        # Create guest user
        username = f'guest_user_{int(time.time())}'
        User.create(db, username, 'password123', 'guest',
                   email=f'{username}@test.com', full_name='Guest User')
        
        response = client.post('/auth/login', json={
            'username': username,
            'password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['role'] == 'guest'

    def test_login_invalid_username(self, client, super_admin_user):
        """Test login with non-existent username."""
        response = client.post('/auth/login', json={
            'username': 'nonexistent_user',
            'password': 'admin123'
        })
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_login_invalid_password(self, client, super_admin_user):
        """Test login with wrong password."""
        response = client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'wrong_password'
        })
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_login_missing_username(self, client):
        """Test login without username."""
        response = client.post('/auth/login', json={
            'password': 'admin123'
        })
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_missing_password(self, client):
        """Test login without password."""
        response = client.post('/auth/login', json={
            'username': 'admin'
        })
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_empty_credentials(self, client):
        """Test login with empty credentials."""
        response = client.post('/auth/login', json={})
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_login_inactive_user(self, client):
        """Test login with inactive user."""
        from app.shared.models import User
        db = client.application.config['DATABASE']
        
        # Create inactive user
        username = f'inactive_{int(time.time())}'
        User.create(db, username, 'password123', 'registered')
        User.update(db, User.get_by_username(db, username)['id'], is_active=0)
        
        response = client.post('/auth/login', json={
            'username': username,
            'password': 'password123'
        })
        assert response.status_code == 401


class TestAuthLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client, super_admin_user):
        """Test successful logout."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.post('/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'redirect' in data

    def test_logout_get_method(self, client, super_admin_user):
        """Test logout with GET method."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.get('/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'

    def test_logout_clears_session(self, client, super_admin_user):
        """Test logout clears session."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        # Verify session has user
        response = client.get('/auth/me')
        assert response.status_code == 200
        
        # Logout
        client.post('/auth/logout')
        
        # Verify session cleared
        response = client.get('/auth/me')
        assert response.status_code == 401


class TestAuthMe:
    """Test /auth/me endpoint."""

    def test_get_current_user(self, client, super_admin_user):
        """Test getting current user info."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.get('/auth/me')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == super_admin_user['id']
        assert data['username'] == super_admin_user['username']
        assert data['role'] == 'super_admin'
        assert data['full_name'] == super_admin_user['full_name']

    def test_me_requires_login(self, client):
        """Test /auth/me requires login."""
        response = client.get('/auth/me')
        assert response.status_code == 401
        assert 'Authentication required' in response.get_json()['error']

    def test_me_after_logout(self, client, super_admin_user):
        """Test /auth/me returns 401 after logout."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        client.post('/auth/logout')
        
        response = client.get('/auth/me')
        assert response.status_code == 401


class TestAuthChangePassword:
    """Test change password endpoint."""

    def test_change_password_success(self, client, super_admin_user):
        """Test successful password change."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123',
            'new_password': 'new_admin123'
        })
        assert response.status_code == 200
        assert 'successfully' in response.get_json()['message']

        # Restore original password - app/DB is shared across tests
        client.post('/auth/change-password', json={
            'old_password': 'new_admin123',
            'new_password': 'admin123'
        })

    def test_change_password_wrong_old(self, client, super_admin_user):
        """Test change password with wrong old password."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.post('/auth/change-password', json={
            'old_password': 'wrong_password',
            'new_password': 'new_admin123'
        })
        assert response.status_code == 400
        assert 'incorrect' in response.get_json()['error']

    def test_change_password_short_new(self, client, super_admin_user):
        """Test change password with too short new password."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123',
            'new_password': '123'
        })
        assert response.status_code == 400
        assert 'at least 6 characters' in response.get_json()['error']

    def test_change_password_missing_fields(self, client, super_admin_user):
        """Test change password with missing fields."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123'
            # missing new_password
        })
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_change_password_requires_login(self, client):
        """Test change password requires login."""
        response = client.post('/auth/change-password', json={
            'old_password': 'admin123',
            'new_password': 'new_password123'
        })
        assert response.status_code == 401


class TestAuthSuperAdminInfo:
    """Test super admin info endpoint."""

    def test_super_admin_info_endpoint(self, client):
        """Test super admin info endpoint accessible without login."""
        response = client.get('/auth/super-admin-info')
        assert response.status_code == 200
        data = response.get_json()
        assert 'name' in data
        assert 'whatsapp' in data
        assert 'note' in data
        assert data['name'] == 'أبو أزاد'
        assert data['whatsapp'] == '+972562150193'


class TestAuthSessionPersistence:
    """Test session persistence across requests."""

    def test_session_persists_across_requests(self, client, super_admin_user):
        """Test session persists across multiple requests."""
        client.post('/auth/login', json={
            'username': super_admin_user['username'],
            'password': 'admin123'
        })
        
        # Make multiple authenticated requests
        for _ in range(5):
            response = client.get('/auth/me')
            assert response.status_code == 200
            data = response.get_json()
            assert data['username'] == super_admin_user['username']

    def test_multiple_users_separate_sessions(self, client):
        """Test multiple users have separate sessions."""
        from app.shared.models import User
        from app import create_app
        
        # Create two users
        db = client.application.config['DATABASE']
        user1 = f'user1_{int(time.time())}'
        user2 = f'user2_{int(time.time())}'
        User.create(db, user1, 'pass123', 'registered')
        User.create(db, user2, 'pass123', 'registered')
        
        # Login as user1
        client.post('/auth/login', json={'username': user1, 'password': 'pass123'})
        resp1 = client.get('/auth/me')
        assert resp1.get_json()['username'] == user1
        
        # Login as user2 (should replace session)
        client.post('/auth/login', json={'username': user2, 'password': 'pass123'})
        resp2 = client.get('/auth/me')
        assert resp2.get_json()['username'] == user2


import time