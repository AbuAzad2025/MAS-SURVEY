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
            'p2': {'y': 100.0, 'x': 0.0},
            'dist1': 50.0,
            'dist2': 50.0
        })
        assert response.status_code == 200


class TestAPIInterpolation:
    """Test interpolation calculation API endpoints."""

    def test_interpolation(self, client, sample_file):
        """Test vertical interpolation API."""
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 2.0,
            'lines': [[1, 2]]
        })
        assert response.status_code == 200

    def test_interpolation_invalid_interval(self, client, sample_file):
        """Test interpolation with invalid interval."""
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 0.0,
            'lines': [[1, 2]]
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


class TestAPIFreeNumbers:
    """Test free numbers API endpoint."""

    def test_get_free_numbers(self, client, sample_file):
        """Test getting free numbers (deleted points)."""
        response = client.post('/api/calculate/freenumbers', json={
            'from_no': 1,
            'to_no': 9999
        })
        assert response.status_code == 200


class TestAPIPrint:
    """Test print-related API endpoints."""

    def test_print_coordinates(self, client, sample_file):
        """Test printing coordinates."""
        response = client.post('/api/print/coordinates', json={'type': 'all'})
        assert response.status_code == 200

    def test_print_grid_limits(self, client, sample_file):
        """Test printing grid limits."""
        response = client.get('/api/print/gridlimits')
        assert response.status_code == 200


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
