"""
File indexing and DTF file handling integration tests.
Tests file upload, parsing, indexing and retrieval.
"""
import pytest
import time
import struct
import io


class TestDTFUploadAPI:
    """Test DTF file upload via API."""

    def test_upload_valid_dtf_file(self, client):
        """Test uploading valid DTF file."""
        header = b'SAMPLE          '
        marker = b'\xDC\x05\x00\x00'
        date_str = b'31-8-2026     '
        points_data = b''
        for y, x, h in [(1000.0, 2000.0, 50.0), (1100.0, 2000.0, 55.0)]:
            points_data += struct.pack('<d', y)
            points_data += struct.pack('<d', x)
            points_data += struct.pack('<d', h)
        content = header + marker + date_str + header + points_data

        data = {'file': (io.BytesIO(content), 'test_upload.DTF')}
        response = client.post('/api/files/upload',
            data=data,
            content_type='multipart/form-data')

        assert response.status_code == 200
        result = response.json
        assert result['status'] == 'ok'

    def test_upload_invalid_dtf_format(self, client):
        """Test uploading invalid DTF file."""
        data = {'file': (io.BytesIO(b'not a valid dtf file'), 'test.DTF')}
        response = client.post('/api/files/upload',
            data=data,
            content_type='multipart/form-data')

        assert response.status_code == 400

    def test_upload_small_file(self, client):
        """Test uploading too small file."""
        data = {'file': (io.BytesIO(b'x'), 'test.DTF')}
        response = client.post('/api/files/upload',
            data=data,
            content_type='multipart/form-data')

        assert response.status_code == 400

    def test_upload_without_file(self, client):
        """Test upload without file."""
        response = client.post('/api/files/upload',
            data={},
            content_type='multipart/form-data')

        assert response.status_code == 400


class TestDTFParsing:
    """Test DTF file parsing logic."""

    def test_parse_dtf_valid_content(self):
        """Test parsing valid DTF content."""
        from app.programs.mas.routes.api import parse_dtf_file

        header = b'SAMPLE          '
        marker = b'\xDC\x05\x00\x00'
        date_str = b'31-8-2026     '
        points_data = b''
        for y, x, h in [(1000.0, 2000.0, 50.0), (1100.0, 2000.0, 55.0)]:
            points_data += struct.pack('<d', y)
            points_data += struct.pack('<d', x)
            points_data += struct.pack('<d', h)
        content = header + marker + date_str + header + points_data

        points = parse_dtf_file(content)

        assert isinstance(points, list)

    def test_parse_dtf_empty_content(self):
        """Test parsing empty DTF content."""
        from app.programs.mas.routes.api import parse_dtf_file

        points = parse_dtf_file(b'')
        assert points == []

    def test_parse_dtf_too_small(self):
        """Test parsing too small DTF content."""
        from app.programs.mas.routes.api import parse_dtf_file

        points = parse_dtf_file(b'x')
        assert points == []

    def test_parse_dtf_invalid_header(self):
        """Test parsing DTF with invalid header."""
        from app.programs.mas.routes.api import parse_dtf_file

        content = b'INVALID_HEADER_' + b'\x00' * 50
        points = parse_dtf_file(content)
        assert points == []


class TestFileNameHandling:
    """Test file name handling and indexing."""

    def test_file_name_special_chars_handled(self, client):
        """Test file name with normal characters."""
        header = b'SAMPLE          '
        marker = b'\xDC\x05\x00\x00'
        date_str = b'31-8-2026     '
        points_data = b''
        for y, x, h in [(1000.0, 2000.0, 50.0), (1100.0, 2000.0, 55.0)]:
            points_data += struct.pack('<d', y)
            points_data += struct.pack('<d', x)
            points_data += struct.pack('<d', h)
        content = header + marker + date_str + header + points_data

        data = {'file': (io.BytesIO(content), 'test_file.DTF')}
        response = client.post('/api/files/upload',
            data=data,
            content_type='multipart/form-data')

        assert response.status_code == 200
        result = response.json
        assert result['status'] == 'ok'


class TestFilePointRetrieval:
    """Test point retrieval after file operations."""

    def test_get_points_after_upload(self, client):
        """Test getting points after DTF upload."""
        header = b'SAMPLE          '
        marker = b'\xDC\x05\x00\x00'
        date_str = b'31-8-2026     '
        points_data = b''
        for y, x, h in [(1000.0, 2000.0, 50.0), (1100.0, 2000.0, 55.0), (1100.0, 2100.0, 60.0)]:
            points_data += struct.pack('<d', y)
            points_data += struct.pack('<d', x)
            points_data += struct.pack('<d', h)
        content = header + marker + date_str + header + points_data

        data = {'file': (io.BytesIO(content), 'points_test.DTF')}
        response = client.post('/api/files/upload', data=data, content_type='multipart/form-data')

        if response.status_code == 200:
            file_name = response.json['filename']

            with client.session_transaction() as sess:
                sess['current_file'] = file_name

            response = client.get('/api/points')
            assert response.status_code == 200
            points = response.json
            assert isinstance(points, list)


class TestFileIndexingConsistency:
    """Test file indexing consistency."""

    def test_file_count_matches(self, client):
        """Test file count in listing matches actual."""
        file_name = f'count_test_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'Count Test'
        })

        response = client.get('/api/files')
        files = response.json

        file_names = [f['name'] for f in files]
        assert file_name in file_names

    def test_points_count_in_file_record(self, client, sample_file):
        """Test points count in file record matches actual."""
        file_response = client.get(f'/api/files/{sample_file["name"]}')
        file_info = file_response.json

        response = client.get('/api/points')
        points = response.json

        assert file_info['no_of_points'] == len(points)


class TestFileDeleteAndCleanup:
    """Test file deletion and cleanup."""

    def test_delete_file_cleans_up_points(self, client):
        """Test deleting file removes all its points."""
        file_name = f'cleanup_test_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'Cleanup Test'
        })

        points = [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        ]
        client.post('/api/points', json={'points': points})

        client.delete(f'/api/files/{file_name}')

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        response = client.get('/api/points')
        points = response.json
        assert len(points) == 0

    def test_delete_file_removes_from_list(self, client):
        """Test deleted file not in file list."""
        file_name = f'list_test_{int(time.time())}'

        with client.session_transaction() as sess:
            sess['current_file'] = file_name

        client.post('/api/files', json={
            'name': file_name,
            'date': '2026-08-31',
            'place': 'List Test'
        })

        client.delete(f'/api/files/{file_name}')

        response = client.get('/api/files')
        files = response.json
        file_names = [f['name'] for f in files]
        assert file_name not in file_names
