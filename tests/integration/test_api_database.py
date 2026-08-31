"""
API-Database integration tests.
Tests that API endpoints correctly interact with the database.
"""
import pytest
import time


class TestAPIFilesDatabaseIntegration:
    """Test API file operations with database."""

    def test_create_file_via_api(self, client):
        """Test creating file via API."""
        file_name = f'test_api_file_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        response = client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'API Test Location'
        })

        assert response.status_code == 200

    def test_list_files_via_api(self, client):
        """Test listing files via API."""
        file_name = f'test_list_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'List Test'
        })

        response = client.get('/api/files')

        assert response.status_code == 200
        files = response.json
        assert any(f['name'] == file_name for f in files)

    def test_get_file_detail_via_api(self, client):
        """Test getting file details via API."""
        file_name = f'test_detail_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'Detail Test'
        })

        response = client.get(f'/api/files/{file_name}')

        assert response.status_code == 200
        data = response.json
        assert data['name'] == file_name

    def test_delete_file_via_api(self, client):
        """Test deleting file via API."""
        file_name = f'test_delete_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'Delete Test'
        })

        response = client.delete(f'/api/files/{file_name}')
        assert response.status_code == 200


class TestAPIPointsDatabaseIntegration:
    """Test API point operations with database."""

    def test_add_points_via_api(self, client, sample_file):
        """Test adding points via API."""
        new_points = [
            {'no': 10, 'y': 3000.0, 'x': 4000.0, 'h': 70.0},
            {'no': 11, 'y': 3100.0, 'x': 4100.0, 'h': 75.0},
        ]

        response = client.post('/api/points', json={'points': new_points})

        assert response.status_code == 200

    def test_get_points_via_api(self, client, sample_file):
        """Test getting points via API."""
        response = client.get('/api/points')

        assert response.status_code == 200
        points = response.json

        assert len(points) >= 3
        assert any(p['no'] == 1 for p in points)
        assert any(p['no'] == 2 for p in points)

    def test_save_points_updates_count(self, client, sample_file):
        """Test saving points updates file count."""
        response = client.get(f'/api/files/{sample_file["name"]}')
        initial_count = response.json['no_of_points']

        new_points = [{'no': 100, 'y': 5000.0, 'x': 6000.0, 'h': 80.0}]
        client.post('/api/points', json={'points': new_points})

        response = client.get(f'/api/files/{sample_file["name"]}')
        new_count = response.json['no_of_points']

        assert new_count == initial_count + 1


class TestAPICalculationsDatabaseIntegration:
    """Test API calculations use database data correctly."""

    def test_area_calculation_with_points(self, client, sample_file):
        """Test area calculation with points array."""
        points = [
            {'y': 1000.0, 'x': 2000.0},
            {'y': 1100.0, 'x': 2000.0},
            {'y': 1100.0, 'x': 2100.0},
            {'y': 1000.0, 'x': 2100.0},
        ]

        response = client.post('/api/calculate/area', json={'points': points})

        assert response.status_code == 200
        data = response.json
        assert 'area' in data
        assert 'perimeter' in data

    def test_traverse_calculation_with_points(self, client):
        """Test traverse calculation with points array."""
        traverse_data = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'azimuth': 0.0, 'distance': 100.0},
            {'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0, 'azimuth': 100.0, 'distance': 100.0}
        ]

        response = client.post('/api/calculate/traverse', json={'points': traverse_data})

        assert response.status_code == 200
        data = response.json
        assert 'adjusted_points' in data

    def test_polar_calculation_with_observations(self, client):
        """Test polar calculation with observations array."""
        polar_data = {
            'type': 'DISTOMAT',
            'station_no': 1,
            'back_azimuth': 0.0,
            'observations': [
                {'no': 2, 'distance': 50.0, 'angle': 50.0, 'h': 0.0}
            ]
        }

        response = client.post('/api/calculate/polar', json=polar_data)

        assert response.status_code == 200
        data = response.json
        assert 'results' in data
        assert len(data['results']) > 0


class TestAPISessionDatabaseIntegration:
    """Test API session state with database."""

    def test_current_file_session(self, client, sample_file):
        """Test current file is tracked in session."""
        with client.session_transaction() as sess:
            assert sess.get('current_file') == sample_file['name']

    def test_set_file_updates_session(self, client):
        """Test setting current file updates session."""
        file_name = f'test_session_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/set-file', json={'filename': file_name})

        response = client.get('/api/current-file')
        assert response.status_code == 200


class TestAPIDataConsistency:
    """Test data consistency between API and database."""

    def test_points_from_api_have_required_fields(self, client, sample_file):
        """Test points from API have all required fields."""
        response = client.get('/api/points')

        assert response.status_code == 200
        points = response.json

        for point in points:
            assert 'no' in point
            assert 'y' in point
            assert 'x' in point
            assert 'h' in point

    def test_no_duplicate_point_numbers(self, client, sample_file):
        """Test no duplicate point numbers within a file."""
        response = client.get('/api/points')

        assert response.status_code == 200
        points = response.json

        point_numbers = [p['no'] for p in points]
        assert len(point_numbers) == len(set(point_numbers))


class TestAPIEdgeCases:
    """Test API edge cases with database."""

    def test_delete_nonexistent_file_returns_success(self, client):
        """Test deleting nonexistent file returns success (idempotent)."""
        response = client.delete('/api/files/nonexistent_file_xyz')
        assert response.status_code == 200

    def test_area_calculation_needs_3_points(self, client):
        """Test area calculation requires at least 3 points."""
        points = [
            {'y': 1000.0, 'x': 2000.0},
            {'y': 1100.0, 'x': 2000.0},
        ]

        response = client.post('/api/calculate/area', json={'points': points})

        assert response.status_code == 400

    def test_traverse_calculation_needs_2_points(self, client):
        """Test traverse calculation requires at least 2 points."""
        traverse_data = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'azimuth': 0.0, 'distance': 100.0}
        ]

        response = client.post('/api/calculate/traverse', json={'points': traverse_data})

        assert response.status_code == 400
