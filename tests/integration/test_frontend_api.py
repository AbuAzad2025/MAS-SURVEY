"""
Frontend-API integration tests.
Tests that frontend templates correctly interact with API endpoints.
"""
import pytest
import time


class TestFrontendAPIRouteConsistency:
    """Test frontend routes match API endpoints."""

    def test_area_page_loads(self, client, sample_file):
        """Test area page loads with file data."""
        response = client.get('/area')
        assert response.status_code == 200
        assert b'AREA' in response.data

    def test_traverse_page_loads(self, client, sample_file):
        """Test traverse page loads with file data."""
        response = client.get('/traverse')
        assert response.status_code == 200

    def test_polar_page_loads(self, client, sample_file):
        """Test polar page loads with file data."""
        response = client.get('/polar')
        assert response.status_code == 200

    def test_intersections_page_loads(self, client, sample_file):
        """Test intersections page loads."""
        response = client.get('/intersections')
        assert response.status_code == 200

    def test_circle_page_loads(self, client, sample_file):
        """Test circle page loads."""
        response = client.get('/circle')
        assert response.status_code == 200

    def test_resection_page_loads(self, client, sample_file):
        """Test resection page loads."""
        response = client.get('/resection')
        assert response.status_code == 200

    def test_implants_page_loads(self, client, sample_file):
        """Test implants page loads."""
        response = client.get('/implants')
        assert response.status_code == 200

    def test_offsets_page_loads(self, client, sample_file):
        """Test offsets page loads."""
        response = client.get('/offsets')
        assert response.status_code == 200

    def test_plotting_page_loads(self, client, sample_file):
        """Test plotting page loads."""
        response = client.get('/plotting')
        assert response.status_code == 200

    def test_plan_page_loads(self, client, sample_file):
        """Test plan page loads."""
        response = client.get('/plan')
        assert response.status_code == 200


class TestFrontendDataConsistency:
    """Test frontend displays data consistently with API."""

    def test_area_page_shows_points(self, client, sample_file):
        """Test area page shows points from API."""
        response = client.get('/area')
        assert response.status_code == 200
        for point in sample_file['points']:
            assert str(point['no']).encode() in response.data
            assert str(point['y']).encode() in response.data

    def test_area_page_shows_file_info(self, client, sample_file):
        """Test area page shows file information."""
        response = client.get('/area')
        assert response.status_code == 200
        assert sample_file['name'].encode() in response.data

    def test_points_count_matches(self, client, sample_file):
        """Test displayed points count matches actual."""
        response = client.get('/area')
        assert response.status_code == 200
        assert sample_file['name'].encode() in response.data


class TestFrontendSessionState:
    """Test frontend session state is maintained."""

    def test_file_selection_persists(self, client, sample_file):
        """Test file selection persists across requests."""
        with client.session_transaction() as sess:
            assert sess.get('current_file') == sample_file['name']

        response = client.get('/area')
        assert response.status_code == 200

        with client.session_transaction() as sess:
            assert sess.get('current_file') == sample_file['name']

    def test_no_file_selected_shows_message(self, client):
        """Test no file selected shows appropriate message."""
        client.get('/')
        response = client.get('/area')
        assert response.status_code == 200
        assert b'No file selected' in response.data


class TestFrontendMenuNavigation:
    """Test frontend menu navigation."""

    def test_mas_menu_loads(self, client, sample_file):
        """Test MAS menu page loads."""
        response = client.get('/mas')
        assert response.status_code == 200
        assert b'MAS' in response.data

    def test_files_page_loads(self, client):
        """Test files management page loads."""
        response = client.get('/files')
        assert response.status_code == 200

    def test_main_menu_loads(self, client):
        """Test main menu page loads."""
        response = client.get('/')
        assert response.status_code == 200


class TestFrontendPrintIntegration:
    """Test frontend print functionality."""

    def test_print_preview_loads(self, client, sample_file):
        """Test print preview page loads."""
        response = client.get('/print-preview')
        assert response.status_code == 200

    def test_print_coordinates_api(self, client, sample_file):
        """Test print coordinates API."""
        response = client.post('/api/print/coordinates',
            json={'type': 'all'},
            content_type='application/json')

        assert response.status_code == 200
        data = response.json
        assert 'points' in data
        assert 'header' in data
