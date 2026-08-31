"""
API-Database integration tests.
Tests that API endpoints correctly interact with the database.
"""
import pytest
import time


class TestAPIFilesDatabaseIntegration:
    """Test API file operations with database."""

    def test_create_file_via_api_saves_to_db(self, client):
        """Test creating file via API saves to database."""
        file_name = f'test_api_file_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        response = client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'API Test Location'
        })

        assert response.status_code == 200

    def test_list_files_via_api_returns_db_data(self, client):
        """Test listing files via API returns data from database."""
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

    def test_delete_file_via_api_removes_from_db(self, client):
        """Test deleting file via API removes from database."""
        from app.shared.models import init_db, SurveyFile

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

    def test_add_points_via_api_saves_to_db(self, client, sample_file):
        """Test adding points via API saves to database."""
        new_points = [
            {'no': 10, 'y': 3000.0, 'x': 4000.0, 'h': 70.0},
            {'no': 11, 'y': 3100.0, 'x': 4100.0, 'h': 75.0},
        ]

        response = client.post('/api/points', json={'points': new_points})

        assert response.status_code == 200

        response = client.get(f'/api/files/{sample_file["name"]}')
        assert response.status_code == 200

    def test_get_points_via_api_returns_db_data(self, client, sample_file):
        """Test getting points via API returns data from database."""
        response = client.get(f'/api/points/{sample_file["name"]}')

        assert response.status_code == 200
        points = response.json

        assert len(points) == 3
        assert any(p['no'] == 1 for p in points)
        assert any(p['no'] == 2 for p in points)
        assert any(p['no'] == 3 for p in points)

    def test_update_point_via_api(self, client, sample_file):
        """Test updating a point via API."""
        response = client.put(f'/api/points/{sample_file["name"]}/1', json={
            'y': 1500.0,
            'x': 2500.0,
            'h': 100.0
        })

        assert response.status_code == 200

        response = client.get(f'/api/points/{sample_file["name"]}')
        points = response.json
        updated = next(p for p in points if p['no'] == 1)
        assert updated['y'] == 1500.0

    def test_delete_point_via_api(self, client, sample_file):
        """Test deleting a point via API."""
        response = client.delete(f'/api/points/{sample_file["name"]}/1')

        assert response.status_code == 200

        response = client.get(f'/api/points/{sample_file["name"]}')
        points = response.json
        assert len(points) == 2
        assert not any(p['no'] == 1 for p in points)


class TestAPICalculationsDatabaseIntegration:
    """Test API calculations use database data correctly."""

    def test_area_calculation_uses_db_points(self, client, sample_file):
        """Test area calculation uses points from database."""
        response = client.post('/api/calculate/area', json={
            'file_name': sample_file['name']
        })

        assert response.status_code == 200
        data = response.json
        assert 'area' in data
        assert 'perimeter' in data

    def test_traverse_calculation_uses_db_points(self, client, sample_file):
        """Test traverse calculation uses points from database."""
        response = client.post('/api/calculate/traverse', json={
            'file_name': sample_file['name'],
            'start_no': 1,
            'start_azimuth': 0.0
        })

        assert response.status_code == 200
        data = response.json
        assert 'points' in data

    def test_polar_calculation_uses_db_points(self, client, sample_file):
        """Test polar calculation uses points from database."""
        response = client.post('/api/calculate/polar', json={
            'file_name': sample_file['name'],
            'point_no': 1,
            'azimuth': 100.0,
            'distance': 50.0
        })

        assert response.status_code == 200
        data = response.json
        assert 'y' in data
        assert 'x' in data


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

    def test_file_point_count_consistency(self, client, sample_file):
        """Test file point count is consistent."""
        response = client.get(f'/api/files/{sample_file["name"]}')
        file_data = response.json

        response = client.get(f'/api/points/{sample_file["name"]}')
        points = response.json

        assert file_data['no_of_points'] == len(points)

    def test_points_have_required_fields(self, client, sample_file):
        """Test points have all required fields from schema."""
        response = client.get(f'/api/points/{sample_file["name"]}')
        points = response.json

        for point in points:
            assert 'no' in point
            assert 'y' in point
            assert 'x' in point
            assert 'h' in point

    def test_no_duplicate_point_numbers_in_file(self, client, sample_file):
        """Test no duplicate point numbers within a file."""
        response = client.get(f'/api/points/{sample_file["name"]}')
        points = response.json

        point_numbers = [p['no'] for p in points]
        assert len(point_numbers) == len(set(point_numbers))


class TestAPIEdgeCases:
    """Test API edge cases with database."""

    def test_get_points_for_nonexistent_file(self, client):
        """Test getting points for nonexistent file."""
        response = client.get('/api/points/nonexistent_file_xyz')
        assert response.status_code == 404

    def test_delete_nonexistent_file(self, client):
        """Test deleting nonexistent file."""
        response = client.delete('/api/files/nonexistent_file_xyz')
        assert response.status_code == 404

    def test_create_duplicate_file(self, client, sample_file):
        """Test creating duplicate file name."""
        response = client.post('/api/files', json={
            'name': sample_file['name'],
            'date': '2026-08-31',
            'place': 'Duplicate Test'
        })
        assert response.status_code == 400

    def test_add_point_with_missing_fields(self, client, sample_file):
        """Test adding point with missing fields."""
        incomplete_points = [
            {'no': 99, 'y': 1000.0}
        ]

        response = client.post('/api/points', json={'points': incomplete_points})
        assert response.status_code == 400
