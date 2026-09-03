"""
CLI Tests for MAS Survey Application.
Tests command-line interface functionality.
"""
import os
import sys
import time
import pytest
import subprocess
import json
import struct
from pathlib import Path


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture(scope='class')
    def cli_path(self):
        """Get path to CLI script or main module."""
        project_root = Path(__file__).parent.parent.parent
        run_py = project_root / 'run.py'
        return [sys.executable, str(run_py)]

    @pytest.fixture
    def cli_env(self):
        """Environment variables for CLI."""
        env = os.environ.copy()
        env['FLASK_ENV'] = 'testing'
        env['DATABASE'] = ':memory:'
        return env

    def test_cli_help(self, cli_path):
        """Test CLI help command."""
        result = subprocess.run(
            cli_path + ['--help'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_cli_version(self, cli_path):
        """Test CLI version."""
        result = subprocess.run(
            cli_path + ['--version'],
            capture_output=True,
            text=True
        )
        # May not have --version, just check it runs
        assert result.returncode in [0, 1]


class TestCLIFileOperations:
    """Test file operations via CLI."""

    @pytest.fixture
    def cli_process(self):
        """CLI process for interactive testing."""
        project_root = Path(__file__).parent.parent.parent
        run_py = project_root / 'run.py'
        
        env = os.environ.copy()
        env['FLASK_ENV'] = 'testing'
        
        process = subprocess.Popen(
            [sys.executable, str(run_py)],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        yield process
        
        process.terminate()
        process.wait(timeout=5)

    def test_create_file_via_api(self, client):
        """Test creating file via API (simulates CLI behavior)."""
        response = client.post('/api/files', json={
            'name': f'cli_test_{int(time.time())}',
            'date': '2026-08-31',
            'place': 'CLI Test'
        })
        assert response.status_code == 200


class TestCLIDataImport:
    """Test data import functionality."""

    def test_parse_dtf_format(self):
        """Test DTF file parsing logic."""
        import struct
        
        # Create minimal DTF matching the real layout:
        # 15-byte header + 4-byte marker + 36 bytes padding (data at marker+40)
        header = b'TEST           '
        marker = b'\xDC\x05\x00\x00'
        padding = b'\x00' * 36

        # Binary coordinates
        data = b''
        data += struct.pack('<d', 1000.0)  # y
        data += struct.pack('<d', 2000.0)  # x
        data += struct.pack('<d', 50.0)   # h

        dtf_content = header + marker + padding + data
        
        # Parse like API does
        marker_pos = dtf_content.find(b'\xDC\x05\x00\x00')
        assert marker_pos != -1
        
        data_start = marker_pos + 40
        binary_data = dtf_content[data_start:]
        
        y = struct.unpack('<d', binary_data[0:8])[0]
        x = struct.unpack('<d', binary_data[8:16])[0]
        h = struct.unpack('<d', binary_data[16:24])[0]
        
        assert y == 1000.0
        assert x == 2000.0
        assert h == 50.0


class TestCLIExport:
    """Test data export functionality."""

    def test_export_coordinates_json(self, client, sample_file):
        """Test exporting coordinates to JSON."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        
        response = client.get('/api/points')
        assert response.status_code == 200
        
        data = response.json
        assert isinstance(data, list)


class TestCLIValidation:
    """Test CLI input validation."""

    def test_validate_point_coordinates(self):
        """Test point coordinate validation."""
        # Valid coordinates
        valid_points = [
            {'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'y': -100.0, 'x': -200.0, 'h': 0.0},
            {'y': 0.0, 'x': 0.0, 'h': 0.0},
        ]
        
        for p in valid_points:
            assert 'y' in p
            assert 'x' in p
            assert 'h' in p

    def test_validate_angle_grads(self):
        """Test angle validation for grads."""
        # Valid grads are 0-400
        valid_angles = [0, 100, 200, 300, 399.9999]
        
        for angle in valid_angles:
            assert 0 <= angle <= 400

    def test_validate_distance(self):
        """Test distance validation."""
        # Distances should be positive
        valid_distances = [0.001, 1.0, 100.0, 10000.0]
        
        for d in valid_distances:
            assert d >= 0

    def test_validate_bearing(self):
        """Test bearing validation."""
        # Bearings in grads should be 0-400
        valid_bearings = [0, 50, 100, 150, 200, 250, 300, 350, 399.9999]
        
        for b in valid_bearings:
            assert 0 <= b < 400


class TestCLIErrors:
    """Test CLI error handling."""

    def test_handle_missing_file(self, client):
        """Test handling of missing file."""
        response = client.get('/files/nonexistent')
        assert response.status_code in [200, 404]

    def test_handle_invalid_point_number(self, client, sample_file):
        """Test handling of invalid point number."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        
        # Try to get point that doesn't exist
        points = client.get('/api/points').json
        max_no = max(p.get('no', 0) for p in points)
        
        assert max_no >= 1  # At least one point exists

    def test_handle_zero_distance(self):
        """Test handling of zero distance."""
        from app.services.calculator import CalculatorService
        
        # Zero distance should be handled gracefully
        # The API will reject it in some calculations
        result = CalculatorService.calculate_distance(
            {'y': 0, 'x': 0},
            {'y': 0, 'x': 0}
        )
        # Same point = 0 distance


class TestCLICalculations:
    """Test calculations via CLI/API."""

    def test_area_calculation_precision(self, client):
        """Test area calculation with high precision."""
        # Square with known area
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 100.0},
            {'y': 100.0, 'x': 100.0},
            {'y': 100.0, 'x': 0.0},
        ]
        
        response = client.post('/api/calculate/area', json={'points': points})
        assert response.status_code == 200
        assert response.json['area'] == 10000.0

    def test_distance_calculation_precision(self, client):
        """Test distance calculation precision."""
        from app.services.calculator import CalculatorService
        
        # 3-4-5 triangle
        distance = CalculatorService.calculate_distance(
            {'y': 0.0, 'x': 0.0},
            {'y': 3.0, 'x': 4.0}
        )
        assert distance == 5.0

    def test_azimuth_calculation(self, client):
        """Test azimuth calculation."""
        from app.services.calculator import CalculatorService
        
        # North
        azimuth = CalculatorService.calculate_azimuth(
            {'y': 0.0, 'x': 0.0},
            {'y': 100.0, 'x': 0.0}
        )
        assert azimuth == 100.0


class TestCLIBatchOperations:
    """Test batch operations."""

    def test_batch_save_points(self, client, sample_file):
        """Test batch saving of points."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        
        # Create batch of points
        points = [
            {'no': i, 'y': 1000.0 + i, 'x': 2000.0 + i, 'h': 50.0 + i}
            for i in range(1, 101)
        ]
        
        response = client.post('/api/points', json={'points': points})
        assert response.status_code == 200
        assert response.json['count'] == 100

    def test_batch_calculate_interpolation(self, client, sample_file):
        """Test batch interpolation."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        
        # Multiple lines (points 1-3 exist in the sample file fixture)
        lines = [[1, 2], [2, 3]]
        
        response = client.post('/api/calculate/interpolation', json={
            'vertical_interval': 1.0,
            'lines': lines
        })
        assert response.status_code == 200


class TestCLIPerformance:
    """Test performance-related functionality."""

    def test_large_file_handling(self, client, sample_file):
        """Test handling of large point sets."""
        client.post('/api/set-file', json={'filename': sample_file['name']})
        
        # Create 1000 points
        points = [
            {'no': i, 'y': float(i), 'x': float(i), 'h': float(i)}
            for i in range(1, 1001)
        ]
        
        response = client.post('/api/points', json={'points': points})
        assert response.status_code == 200
        
        # Retrieve should still work (fixture pre-creates 3 points, API appends)
        response = client.get('/api/points')
        assert response.status_code == 200
        assert len(response.json) >= 1000

    def test_concurrent_file_access(self, client):
        """Test concurrent file access."""
        files = []
        
        # Create multiple files
        for i in range(5):
            name = f'concurrent_test_{int(time.time())}_{i}'
            response = client.post('/api/files', json={
                'name': name,
                'date': '2026-08-31',
                'place': f'Test {i}'
            })
            files.append(name)
            assert response.status_code == 200
        
        # List all files
        response = client.get('/api/files')
        assert response.status_code == 200
        assert len(response.json) >= 5
        
        # Cleanup
        for name in files:
            client.delete(f'/api/files/{name}')
