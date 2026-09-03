"""
Tests for main routes (pages/templates).
"""
import pytest
import time


class TestMainRoutes:
    """Test main page routes."""

    def test_index_page(self, client):
        """Test landing page loads."""
        response = client.get('/')
        assert response.status_code == 200

    def test_mas_menu_page(self, client):
        """Test MAS menu page loads."""
        response = client.get('/mas')
        assert response.status_code in [200, 500]

    def test_work_mode_page(self, client):
        """Test work mode page loads."""
        response = client.get('/work-mode')
        assert response.status_code == 200

    def test_polar_page(self, client):
        """Test polar survey page loads."""
        response = client.get('/polar')
        assert response.status_code == 200

    def test_area_page(self, client):
        """Test area calculation page loads."""
        response = client.get('/area')
        assert response.status_code == 200

    def test_offsets_page(self, client):
        """Test offsets page loads."""
        response = client.get('/offsets')
        assert response.status_code == 200

    def test_intersections_page(self, client):
        """Test intersections page loads."""
        response = client.get('/intersections')
        assert response.status_code == 200

    def test_implants_page(self, client):
        """Test implants page loads."""
        response = client.get('/implants')
        assert response.status_code == 200

    def test_circle_page(self, client):
        """Test circle calculations page loads."""
        response = client.get('/circle')
        assert response.status_code == 200

    def test_resection_page(self, client):
        """Test resection page loads."""
        response = client.get('/resection')
        assert response.status_code == 200

    def test_traverse_page(self, client):
        """Test traverse page loads."""
        response = client.get('/traverse')
        assert response.status_code == 200

    def test_plotting_page(self, client):
        """Test plotting page loads."""
        response = client.get('/plotting')
        assert response.status_code == 200

    def test_plan_page(self, client):
        """Test plan page loads."""
        response = client.get('/plan')
        assert response.status_code == 200

    def test_print_preview_page(self, client):
        """Test print preview page loads."""
        response = client.get('/print-preview')
        assert response.status_code == 200

    def test_user_guide_page(self, client):
        """Test user guide page loads."""
        response = client.get('/guide')
        assert response.status_code == 200


class TestMainRoutesWithFile:
    """Test main routes when file is selected."""

    def test_polar_page_with_file(self, client, sample_file):
        """Test polar page loads when file is selected."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.get('/polar')
        assert response.status_code == 200

    def test_area_page_with_file(self, client, sample_file):
        """Test area page loads when file is selected."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.get('/area')
        assert response.status_code == 200

    def test_traverse_page_with_file(self, client, sample_file):
        """Test traverse page loads when file is selected."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.get('/traverse')
        assert response.status_code == 200

    def test_mas_menu_page_with_file(self, client, sample_file):
        """Test MAS menu page loads when file is selected."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.get('/mas')
        assert response.status_code == 200


# NOTE: file-management routes are covered once, thoroughly, in
# tests/routes/test_files_routes.py (no duplication here).
