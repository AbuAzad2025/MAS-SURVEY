"""
Tests for files routes.
"""
import pytest
import time


class TestFilesRoutes:
    """Test file management routes."""

    def test_list_files_get(self, client):
        """Test listing files via GET."""
        response = client.get('/files')
        assert response.status_code == 200

    def test_new_file_get(self, client):
        """Test new file form page."""
        response = client.get('/files/new')
        assert response.status_code == 200

    def test_new_file_post_success(self, client):
        """Test creating file via POST."""
        name = f'test_{int(time.time())}'
        response = client.post('/files/new', data={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test Location'
        }, follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_new_file_post_empty_name(self, client):
        """Test creating file with empty name returns 400."""
        response = client.post('/files/new', data={
            'name': '',
            'date': '2026-08-31',
            'place': 'Test'
        })
        assert response.status_code == 400
        assert b'File name is required' in response.data

    def test_view_file_success(self, client):
        """Test viewing existing file."""
        name = f'test_{int(time.time())}'
        client.post('/api/files', json={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        response = client.get(f'/files/{name}')
        assert response.status_code == 200

    def test_view_file_not_found(self, client):
        """Test viewing non-existent file returns 404."""
        response = client.get('/files/nonexistent_file_xyz')
        assert response.status_code == 404
        assert b'File not found' in response.data

    def test_delete_file_post(self, client):
        """Test deleting file via POST."""
        name = f'test_{int(time.time())}'
        client.post('/api/files', json={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        client.post('/api/set-file', json={'filename': name})
        response = client.post(f'/files/{name}/delete', follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_delete_file_get_not_allowed(self, client):
        """Test delete via GET returns 405."""
        name = f'test_{int(time.time())}'
        client.post('/api/files', json={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        response = client.get(f'/files/{name}/delete')
        assert response.status_code == 405

    def test_new_file_post_duplicate(self, client):
        """Test creating duplicate file returns 400."""
        name = f'test_{int(time.time())}'
        client.post('/files/new', data={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        response = client.post('/files/new', data={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        assert response.status_code == 400
        assert b'already exists' in response.data
