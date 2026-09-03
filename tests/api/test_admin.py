"""
Admin API Tests for MAS Survey Application.
Tests all Super Admin panel API endpoints.
"""
import pytest
import json
import time
from typing import Dict, List, Any


class TestAdminAuth:
    """Test admin authentication and authorization."""

    def test_admin_dashboard_requires_super_admin(self, client):
        """Test admin dashboard requires super_admin role."""
        # Login as regular user first
        from app.shared.models import User
        from app import create_app
        
        # Create a regular user
        db = client.application.config['DATABASE']
        User.create(db, 'regular_user', 'password123', 'registered', 
                   email='regular@test.com', full_name='Regular User')
        
        client.post('/auth/login', json={'username': 'regular_user', 'password': 'password123'})
        
        # Try to access admin dashboard
        response = client.get('/admin/')
        assert response.status_code == 403  # Forbidden - not super_admin

    def test_admin_dashboard_accessible_by_super_admin(self, client, super_admin_user):
        """Test admin dashboard accessible by super_admin."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/')
        assert response.status_code == 200

    def test_admin_api_requires_super_admin(self, client):
        """Test admin API endpoints require super_admin role."""
        response = client.get('/admin/api/users')
        assert response.status_code == 401  # Not logged in
        
        # Login as regular user
        from app.shared.models import User
        db = client.application.config['DATABASE']
        User.create(db, 'regular_user2', 'password123', 'registered')
        client.post('/auth/login', json={'username': 'regular_user2', 'password': 'password123'})
        
        response = client.get('/admin/api/users')
        assert response.status_code == 403  # Forbidden


class TestAdminUsersAPI:
    """Test user management API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client, super_admin_user):
        """Setup: login as super_admin before each test."""
        self.client = client
        self.super_admin_user = super_admin_user
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})

    def test_list_users(self, client):
        """Test listing all users."""
        response = client.get('/admin/api/users')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least super_admin

    def test_create_user_registered(self, client):
        """Test creating a registered user."""
        username = f'new_user_{int(time.time())}'
        response = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered',
            'email': f'{username}@test.com',
            'full_name': 'New Test User'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['user']['username'] == username
        assert data['user']['role'] == 'registered'

    def test_create_user_super_admin(self, client):
        """Test creating another super_admin."""
        username = f'super_admin2_{int(time.time())}'
        response = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'super_admin',
            'email': f'{username}@test.com',
            'full_name': 'Super Admin 2'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['role'] == 'super_admin'

    def test_create_user_guest(self, client):
        """Test creating a guest user."""
        username = f'guest_user_{int(time.time())}'
        response = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'guest'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['role'] == 'guest'

    def test_create_user_duplicate_username(self, client):
        """Test creating user with duplicate username fails."""
        username = f'dup_user_{int(time.time())}'
        # Create first user
        client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered'
        })
        # Try to create second with same username
        response = client.post('/admin/api/users', json={
            'username': username,
            'password': 'different123',
            'role': 'registered'
        })
        assert response.status_code == 400
        assert 'already exists' in response.get_json()['error']

    def test_create_user_invalid_role(self, client):
        """Test creating user with invalid role fails."""
        response = client.post('/admin/api/users', json={
            'username': f'invalid_role_{int(time.time())}',
            'password': 'password123',
            'role': 'invalid_role'
        })
        assert response.status_code == 400
        assert 'Invalid role' in response.get_json()['error']

    def test_create_user_short_password(self, client):
        """Test creating user with short password fails."""
        response = client.post('/admin/api/users', json={
            'username': f'short_pwd_{int(time.time())}',
            'password': '123',
            'role': 'registered'
        })
        assert response.status_code == 400
        assert 'at least 6 characters' in response.get_json()['error']

    def test_create_user_missing_fields(self, client):
        """Test creating user with missing required fields fails."""
        response = client.post('/admin/api/users', json={
            'username': 'test'
            # missing password
        })
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']

    def test_get_user(self, client):
        """Test getting user details."""
        # First create a user
        username = f'get_user_{int(time.time())}'
        create_resp = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered'
        })
        user_id = create_resp.get_json()['user']['id']
        
        # Get user
        response = client.get(f'/admin/api/users/{user_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['username'] == username
        assert data['role'] == 'registered'

    def test_get_user_not_found(self, client):
        """Test getting non-existent user."""
        response = client.get('/admin/api/users/99999')
        assert response.status_code == 404

    def test_update_user(self, client):
        """Test updating user."""
        username = f'update_user_{int(time.time())}'
        create_resp = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered'
        })
        user_id = create_resp.get_json()['user']['id']
        
        # Update user
        response = client.put(f'/admin/api/users/{user_id}', json={
            'full_name': 'Updated Name',
            'email': 'updated@test.com',
            'role': 'guest'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['full_name'] == 'Updated Name'
        assert data['user']['role'] == 'guest'

    def test_update_user_cannot_modify_self(self, client, super_admin_user):
        """Test super_admin cannot modify themselves via API."""
        response = client.put(f'/admin/api/users/{super_admin_user["id"]}', json={
            'full_name': 'Hacked Name'
        })
        assert response.status_code == 400
        assert 'Cannot modify yourself' in response.get_json()['error']

    def test_delete_user(self, client):
        """Test deleting (soft delete) user."""
        username = f'delete_user_{int(time.time())}'
        create_resp = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered'
        })
        user_id = create_resp.get_json()['user']['id']
        
        # Delete user
        response = client.delete(f'/admin/api/users/{user_id}')
        assert response.status_code == 200
        assert response.get_json()['status'] == 'ok'
        
        # Verify user is deactivated
        get_resp = client.get(f'/admin/api/users/{user_id}')
        assert get_resp.status_code == 200
        assert get_resp.get_json()['is_active'] == 0

    def test_delete_user_cannot_delete_self(self, client, super_admin_user):
        """Test super_admin cannot delete themselves."""
        response = client.delete(f'/admin/api/users/{super_admin_user["id"]}')
        assert response.status_code == 400
        assert 'Cannot delete yourself' in response.get_json()['error']

    def test_reset_password(self, client):
        """Test resetting user password."""
        username = f'reset_pwd_{int(time.time())}'
        create_resp = client.post('/admin/api/users', json={
            'username': username,
            'password': 'old_password123',
            'role': 'registered'
        })
        user_id = create_resp.get_json()['user']['id']
        
        # Reset password
        response = client.post(f'/admin/api/users/{user_id}/reset-password', json={
            'new_password': 'new_password123'
        })
        assert response.status_code == 200
        assert 'successfully' in response.get_json()['message']
        
        # Verify new password works
        from app.shared.models import User
        db = client.application.config['DATABASE']
        auth_user = User.authenticate(db, username, 'new_password123')
        assert auth_user is not None

    def test_reset_password_short(self, client):
        """Test resetting password with too short password fails."""
        username = f'reset_short_{int(time.time())}'
        create_resp = client.post('/admin/api/users', json={
            'username': username,
            'password': 'password123',
            'role': 'registered'
        })
        user_id = create_resp.get_json()['user']['id']
        
        response = client.post(f'/admin/api/users/{user_id}/reset-password', json={
            'new_password': '123'
        })
        assert response.status_code == 400
        assert 'at least 6 characters' in response.get_json()['error']


class TestAdminStatsAPI:
    """Test admin statistics API."""

    def test_get_stats(self, client, super_admin_user):
        """Test getting system statistics."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/api/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_users' in data
        assert 'super_admins' in data
        assert 'registered_users' in data
        assert 'guests' in data
        assert 'active_users' in data
        assert 'total_files' in data
        assert 'total_points' in data


class TestAdminSettings:
    """Test admin settings page."""

    def test_settings_page_accessible(self, client, super_admin_user):
        """Test settings page accessible by super_admin."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/settings')
        assert response.status_code == 200


class TestAdminLogs:
    """Test admin logs API."""

    def test_get_logs(self, client, super_admin_user):
        """Test getting system logs."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/api/logs')
        assert response.status_code == 200
        data = response.get_json()
        assert 'logs' in data

    def test_get_logs_with_filter(self, client, super_admin_user):
        """Test getting logs with level filter."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/api/logs?level=ERROR')
        assert response.status_code == 200
        data = response.get_json()
        assert 'logs' in data

    def test_clear_logs(self, client, super_admin_user):
        """Test clearing all logs."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.delete('/admin/api/logs')
        assert response.status_code == 200
        assert response.get_json()['status'] == 'ok'


class TestAdminFiles:
    """Test admin files overview."""

    def test_files_page(self, client, super_admin_user):
        """Test files overview page."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        
        response = client.get('/admin/files')
        assert response.status_code == 200


class TestAdminNavigation:
    """Test admin navigation endpoints."""

    def test_dashboard_page(self, client, super_admin_user):
        """Test dashboard page."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        response = client.get('/admin/')
        assert response.status_code == 200

    def test_logs_page(self, client, super_admin_user):
        """Test logs page."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        response = client.get('/admin/logs')
        assert response.status_code == 200

    def test_files_page(self, client, super_admin_user):
        """Test files page."""
        client.post('/auth/login', json={'username': super_admin_user['username'], 'password': 'admin123'})
        response = client.get('/admin/files')
        assert response.status_code == 200


import time