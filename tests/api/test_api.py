"""
API Tests for MAS Survey Application.
Tests all REST API endpoints.
"""
import pytest
import json
import time
from typing import Dict, List, Any


class TestAPIHealth:
    """Test API health and basic endpoints."""

    def test_api_health_check(self, client):
        """Test API is responding."""
        response = client.get('/')
        assert response.status_code == 200


class TestAPIFiles:
    """Test file management API endpoints."""

    def test_create_file(self, client):
        """Test creating a new survey file."""
        response = client.post('/api/files', json={
            'name': f'test_api_{int(time.time())}',
            'date': '2026-08-31',
            'place': 'API Test Location'
        })
        assert response.status_code == 200

    def test_list_files(self, client):
        """Test listing all files."""
        response = client.get('/api/files')
        assert response.status_code == 200

    def test_get_file_detail(self, client):
        """Test getting file details."""
        name = f'test_file_{int(time.time())}'
        client.post('/api/files', json={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        response = client.get(f'/api/files/{name}')
        assert response.status_code == 200

    def test_delete_file(self, client):
        """Test deleting a file."""
        name = f'test_file_{int(time.time())}'
        client.post('/api/files', json={
            'name': name,
            'date': '2026-08-31',
            'place': 'Test'
        })
        response = client.delete(f'/api/files/{name}')
        assert response.status_code == 200


class TestAPIPoints:
    """Test point management API endpoints."""

    def test_save_points(self, client, sample_file):
        """Test saving points via API."""
        points = [
            {'no': 10, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 11, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        ]
        response = client.post('/api/points', json={'points': points})
        assert response.status_code == 200

    def test_get_points(self, client, sample_file):
        """Test retrieving points."""
        response = client.get('/api/points')
        assert response.status_code == 200


class TestAPICalculations:
    """Test calculation API endpoints."""

    def test_calculate_area(self, client):
        """Test area calculation API."""
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 10.0},
            {'y': 10.0, 'x': 10.0},
            {'y': 10.0, 'x': 0.0},
        ]
        response = client.post('/api/calculate/area', json={'points': points})
        assert response.status_code == 200

    def test_calculate_perimeter(self, client):
        """Test perimeter calculation API."""
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 10.0},
            {'y': 10.0, 'x': 10.0},
            {'y': 10.0, 'x': 0.0},
        ]
        response = client.post('/api/calculate/perimeter', json={'points': points})
        assert response.status_code == 200

    def test_calculate_polar(self, client):
        """Test polar calculation API."""
        response = client.post('/api/calculate/polar', json={
            'type': 'DISTOMAT',
            'station_no': 1,
            'back_azimuth': 0,
            'observations': [
                {'no': 10, 'distance': 100, 'angle': 50, 'v_angle': 0, 'h': 0}
            ]
        })
        assert response.status_code == 200

    def test_calculate_intersection_two_lines(self, client):
        """Test two lines intersection API."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'TWO_LINES',
            'p1': {'y': 0.0, 'x': 0.0},
            'bearing1': 100.0,
            'p2': {'y': 100.0, 'x': 100.0},
            'bearing2': 200.0
        })
        assert response.status_code == 200

    def test_calculate_intersection_parallel_lines(self, client):
        """Test parallel lines intersection returns error."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'TWO_LINES',
            'p1': {'y': 0.0, 'x': 0.0},
            'bearing1': 100.0,
            'p2': {'y': 100.0, 'x': 0.0},
            'bearing2': 100.0
        })
        assert response.status_code == 400

    def test_calculate_intersection_two_circles(self, client):
        """Test two circles intersection API."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'TWO_CIRCLES',
            'p1': {'y': 0.0, 'x': 0.0},
            'distance1': 100.0,
            'p2': {'y': 100.0, 'x': 0.0},
            'distance2': 100.0
        })
        assert response.status_code in [200, 400]

    def test_calculate_intersection_non_intersecting_circles(self, client):
        """Test non-intersecting circles returns error."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'TWO_CIRCLES',
            'p1': {'y': 0.0, 'x': 0.0},
            'distance1': 10.0,
            'p2': {'y': 100.0, 'x': 0.0},
            'distance2': 10.0
        })
        assert response.status_code == 400

    def test_calculate_intersection_line_distance(self, client):
        """Test line-circle intersection API."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'LINE_DISTANCE',
            'p1': {'y': 0.0, 'x': 0.0},
            'bearing1': 90.0,
            'p2': {'y': 50.0, 'x': 50.0},
            'distance2': 30.0
        })
        assert response.status_code in [200, 400]

    def test_calculate_intersection_unknown_type(self, client):
        """Test unknown intersection type returns error."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'UNKNOWN',
            'p1': {'y': 0.0, 'x': 0.0}
        })
        assert response.status_code == 400

    def test_calculate_intersection_two_distances(self, client):
        """Test two distances intersection API."""
        response = client.post('/api/calculate/intersection', json={
            'type': 'TWO_DISTANCES',
            'p1': {'y': 0.0, 'x': 0.0},
            'distance1': 100.0,
            'p2': {'y': 100.0, 'x': 0.0},
            'distance2': 100.0
        })
        assert response.status_code == 200

    def test_calculate_implant(self, client):
        """Test implant calculation API."""
        response = client.post('/api/calculate/implant', json={
            'base_point': {'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            'distance': 50.0,
            'bearing': 100.0,
            'height': 55.0
        })
        assert response.status_code == 200

    def test_calculate_circle_arc(self, client):
        """Test circle arc calculation API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'ARC',
            'value1': 100.0,
            'value2': 50.0
        })
        assert response.status_code == 200

    def test_calculate_circle_circumference(self, client):
        """Test circle circumference API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'CIRCUMFERENCE',
            'value1': 50.0
        })
        assert response.status_code == 200

    def test_calculate_circle_area(self, client):
        """Test circle area API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'AREA',
            'value1': 50.0
        })
        assert response.status_code == 200

    def test_calculate_circle_center(self, client):
        """Test circle center from 3 points API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'CENTER',
            'p1': {'y': 0.0, 'x': 0.0},
            'p2': {'y': 6.0, 'x': 0.0},
            'p3': {'y': 0.0, 'x': 8.0}
        })
        assert response.status_code == 200


class TestAPIOffsets:
    """Test offsets calculation API."""

    def test_calculate_offsets(self, client):
        """Test offsets calculation API."""
        response = client.post('/api/calculate/offsets', json={
            'line_start': {'y': 0, 'x': 0},
            'line_end': {'y': 100, 'x': 100},
            'points': [
                {'no': 1, 'offset_distance': 10, 'side': 'LEFT'}
            ]
        })
        assert response.status_code == 200


    def test_calculate_circle_collinear_points(self, client):
        """Test circle center with collinear points returns error."""
        response = client.post('/api/calculate/circle', json={
            'type': 'CENTER',
            'p1': {'y': 0.0, 'x': 0.0},
            'p2': {'y': 1.0, 'x': 1.0},
            'p3': {'y': 2.0, 'x': 2.0}
        })
        assert response.status_code == 400

    def test_calculate_circle_radius(self, client):
        """Test circle radius calculation API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'RADIUS',
            'value1': 314.159,
            'value2': 100.0
        })
        assert response.status_code == 200

    def test_calculate_circle_chord(self, client):
        """Test circle chord calculation API."""
        response = client.post('/api/calculate/circle', json={
            'type': 'CHORD',
            'value1': 50.0,
            'value2': 100.0
        })
        assert response.status_code == 200


class TestAPIResection:
    """Test resection calculation API endpoints."""

    def test_resection_3point(self, client):
        """Test 3-point resection API."""
        response = client.post('/api/calculate/resection', json={
            'type': '3POINTS',
            'p1': {'y': 0.0, 'x': 0.0},
            'p2': {'y': 0.0, 'x': 100.0},
            'p3': {'y': 100.0, 'x': 100.0},
            'angle1': 50.0,
            'angle2': 50.0,
            'angle3': 50.0
        })
        assert response.status_code == 200

    def test_resection_2point(self, client):
        """Test 2-point resection API."""
        response = client.post('/api/calculate/resection', json={
            'type': '2POINTS',
            'p1': {'y': 0.0, 'x': 0.0},
            'p2': {'y': 0.0, 'x': 6.0},
            'dist1': 5.0,
            'dist2': 5.0
        })
        assert response.status_code == 200

    def test_resection_unknown_type(self, client):
        """Test unknown resection type returns error."""
        response = client.post('/api/calculate/resection', json={
            'type': 'UNKNOWN'
        })
        assert response.status_code == 400

    def test_resection_2point_failed(self, client):
        """Test 2-point resection with impossible distances."""
        response = client.post('/api/calculate/resection', json={
            'type': '2POINTS',
            'p1': {'y': 0.0, 'x': 0.0},
            'p2': {'y': 0.0, 'x': 6.0},
            'dist1': 100.0,
            'dist2': 100.0
        })
        assert response.status_code in [200, 400]


class TestAPIInterpolation:
    """Test interpolation calculation API endpoints."""

    def test_interpolation_requires_file(self, client, sample_file):
        """Test interpolation requires current file."""
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 2.0,
            'lines': [[1, 2]]
        })
        assert response.status_code == 400

    def test_interpolation_invalid_interval(self, client, sample_file):
        """Test interpolation with invalid interval."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 0.0,
            'lines': [[1, 2]]
        })
        assert response.status_code == 400

    def test_interpolation_no_lines(self, client, sample_file):
        """Test interpolation with no lines specified."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 2.0,
            'lines': []
        })
        assert response.status_code == 400


class TestAPITraverse:
    """Test traverse calculation API endpoints."""

    def test_bowditch_traverse(self, client):
        """Test Bowditch traverse adjustment API."""
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0,
             'azimuth': 0.0, 'distance': 100.0,
             'delta_y': 100.0, 'delta_x': 0.0},
            {'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0,
             'azimuth': 100.0, 'distance': 100.0,
             'delta_y': 0.0, 'delta_x': 100.0},
        ]
        response = client.post('/api/calculate/traverse', json={
            'points': points,
            'known_start': {'y': 0.0, 'x': 0.0},
            'known_end': {'y': 0.0, 'x': 0.0}
        })
        assert response.status_code == 200

    def test_bowditch_insufficient_points(self, client):
        """Test traverse with insufficient points."""
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'distance': 100.0, 'delta_y': 100.0, 'delta_x': 0.0}
        ]
        response = client.post('/api/calculate/traverse', json={'points': points})
        assert response.status_code == 400

    def test_bowditch_zero_distance(self, client):
        """Test traverse with zero total distance."""
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0,
             'azimuth': 0.0, 'distance': 0.0,
             'delta_y': 0.0, 'delta_x': 0.0},
            {'no': 2, 'y': 0.0, 'x': 0.0, 'h': 0.0,
             'azimuth': 100.0, 'distance': 0.0,
             'delta_y': 0.0, 'delta_x': 0.0},
        ]
        response = client.post('/api/calculate/traverse', json={
            'points': points,
            'known_start': {'y': 0.0, 'x': 0.0},
            'known_end': {'y': 0.0, 'x': 0.0}
        })
        assert response.status_code == 400


class TestAPIFreeNumbers:
    """Test free numbers API endpoint."""

    def test_get_free_numbers(self, client, sample_file):
        """Test getting free numbers (deleted points)."""
        response = client.post('/api/calculate/freenumbers', json={
            'from_no': 1,
            'to_no': 9999
        })
        assert response.status_code == 200

    def test_freenumbers_no_file(self, client):
        """Test freenumbers without file selected."""
        response = client.post('/api/calculate/freenumbers', json={
            'from_no': 1,
            'to_no': 9999
        })
        assert response.status_code == 400


class TestAPIPrint:
    """Test print-related API endpoints."""

    def test_print_coordinates(self, client, sample_file):
        """Test printing coordinates."""
        response = client.post('/api/print/coordinates', json={'type': 'all'})
        assert response.status_code == 200

    def test_print_coordinates_single(self, client, sample_file):
        """Test printing single coordinate."""
        response = client.post('/api/print/coordinates', json={'type': 'single', 'from_no': 1})
        assert response.status_code == 200

    def test_print_coordinates_group(self, client, sample_file):
        """Test printing coordinate group."""
        response = client.post('/api/print/coordinates', json={'type': 'group', 'from_no': 1, 'to_no': 10})
        assert response.status_code == 200

    def test_print_freenumbers(self, client, sample_file):
        """Test printing free numbers."""
        response = client.post('/api/print/freenumbers', json={'from_no': 1, 'to_no': 100})
        assert response.status_code == 200

    def test_print_gridlimits(self, client, sample_file):
        """Test printing grid limits."""
        response = client.get('/api/print/gridlimits')
        assert response.status_code == 200

    def test_print_draw_with_heights(self, client, sample_file):
        """Test print draw with heights."""
        response = client.get('/api/print/draw')
        assert response.status_code == 200

    def test_print_draw_no_heights(self, client):
        """Test print draw without heights returns error JSON."""
        with client.session_transaction() as sess:
            sess.clear()
        name = f'test_no_heights_{int(time.time())}'
        client.post('/api/files', json={'name': name, 'date': '2026-08-31', 'place': 'Test'})
        client.post('/api/set-file', json={'filename': name})
        response = client.get('/api/print/draw')
        assert response.status_code == 200
        assert response.json.get('error') == 'no_heights'

    def test_print_coordinates_no_file(self, client):
        """Test print coordinates without file."""
        response = client.post('/api/print/coordinates', json={'type': 'all'})
        assert response.status_code == 400

    def test_print_gridlimits_no_file(self, client):
        """Test print grid limits without file."""
        response = client.get('/api/print/gridlimits')
        assert response.status_code == 400

    def test_print_draw_no_file(self, client):
        """Test print draw without file."""
        response = client.get('/api/print/draw')
        assert response.status_code == 400


class TestAPISettings:
    """Test settings API endpoints."""

    def test_get_settings(self, client):
        """Test getting settings."""
        response = client.get('/api/settings')
        assert response.status_code == 200

    def test_update_settings(self, client):
        """Test updating settings."""
        response = client.post('/api/settings', json={
            'angle_unit': 'GRADS',
            'company_name': 'Test Company'
        })
        assert response.status_code == 200


class TestAPICurrentFile:
    """Test current file API endpoints."""

    def test_set_current_file_empty(self, client):
        """Test setting current file with empty name."""
        response = client.post('/api/set-file', json={'filename': ''})
        assert response.status_code == 400

    def test_set_current_file_success(self, client, sample_file):
        """Test setting current file successfully."""
        response = client.post('/api/set-file', json={'filename': sample_file['name']})
        assert response.status_code == 200

    def test_get_current_file_none(self, client):
        """Test getting current file when none set."""
        response = client.get('/api/current-file')
        assert response.status_code == 200
        assert response.json['file'] is None

    def test_get_current_file_set(self, client, sample_file):
        """Test getting current file when set."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        response = client.get('/api/current-file')
        assert response.status_code == 200
        assert response.json['file'] is not None


class TestAPIFileUpload:
    """Test file upload API endpoint."""

    def test_upload_no_file(self, client):
        """Test upload with no file."""
        response = client.post('/api/files/upload')
        assert response.status_code == 400

    def test_upload_empty_filename(self, client):
        """Test upload with empty filename."""
        import io
        data = {'file': (io.BytesIO(b'test'), '')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_invalid_type(self, client):
        """Test upload with invalid file type."""
        import io
        data = {'file': (io.BytesIO(b'test content'), 'test.txt')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_file_too_large(self, client):
        """Test upload with file too large."""
        import io
        large_content = b'x' * (11 * 1024 * 1024)
        data = {'file': (io.BytesIO(large_content), 'test.DTF')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_file_too_small(self, client):
        """Test upload with file too small."""
        import io
        data = {'file': (io.BytesIO(b'x'), 'test.DTF')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    def test_upload_invalid_dtf(self, client):
        """Test upload with invalid DTF content."""
        import io
        data = {'file': (io.BytesIO(b'not a valid dtf file content here'), 'test.DTF')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400


class TestAPIPointsEdge:
    """Test points API edge cases."""

    def test_get_points_no_file(self, client):
        """Test getting points when no file is set."""
        response = client.get('/api/points')
        assert response.status_code == 200
        assert response.json == []

    def test_save_points_no_file(self, client):
        """Test saving points when no file is set."""
        response = client.post('/api/points', json={'points': []})
        assert response.status_code == 400

    def test_create_file_empty_name(self, client):
        """Test creating file with empty name."""
        response = client.post('/api/files', json={'name': '   ', 'date': '', 'place': ''})
        assert response.status_code == 400

    def test_get_file_not_found(self, client):
        """Test getting non-existent file."""
        response = client.get('/api/files/nonexistent_file_xyz')
        assert response.status_code == 404

    def test_get_guide(self, client):
        """Test getting user guide."""
        response = client.get('/api/guide')
        assert response.status_code == 200


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/calculate/area',
            data='not json',
            content_type='application/json'
        )
        assert response.status_code >= 400

    def test_missing_required_field(self, client):
        """Test handling of missing required fields."""
        response = client.post('/api/calculate/area', json={})
        assert response.status_code == 400
