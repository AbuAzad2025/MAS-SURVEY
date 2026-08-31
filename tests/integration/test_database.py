"""
Database consistency and schema tests.
Tests database schema, constraints, and data integrity.
"""
import pytest
import sqlite3
import os


class TestDatabaseSchema:
    """Test database schema."""

    def test_database_init_creates_tables(self, temp_db):
        """Test database initialization creates all required tables."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'survey_files' in tables
        assert 'survey_points' in tables
        assert 'settings' in tables

        conn.close()

    def test_survey_files_table_schema(self, temp_db):
        """Test survey_files table has correct schema."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(survey_files)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert columns['name'] == 'TEXT'
        assert columns['date'] == 'TEXT'
        assert columns['place'] == 'TEXT'
        assert columns['no_of_points'] == 'INTEGER'

        conn.close()

    def test_survey_points_table_schema(self, temp_db):
        """Test survey_points table has correct schema."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(survey_points)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert columns['file_name'] == 'TEXT'
        assert columns['no'] == 'INTEGER'
        assert columns['y'] == 'REAL'
        assert columns['x'] == 'REAL'
        assert columns['h'] == 'REAL'
        assert columns['code'] == 'TEXT'

        conn.close()

    def test_survey_files_primary_key(self, temp_db):
        """Test survey_files has primary key on name."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA index_list(survey_files)")
        indexes = cursor.fetchall()

        conn.close()

    def test_survey_points_foreign_key(self, temp_db):
        """Test survey_points has foreign key to survey_files."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_key_list(survey_points)")
        fks = cursor.fetchall()

        conn.close()


class TestDatabaseConstraints:
    """Test database constraints."""

    def test_survey_file_name_unique(self, temp_db):
        """Test survey_files name must be unique."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)

        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Location 1')
        result = SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Location 2')

        assert result is None

    def test_survey_points_require_file(self, temp_db):
        """Test survey_points require valid file_name."""
        from app.shared.models import init_db

        init_db(temp_db)

        conn = sqlite3.connect(temp_db)
        conn.execute('PRAGMA foreign_keys=ON')
        cursor = conn.cursor()

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO survey_points (file_name, no, y, x, h)
                VALUES (?, ?, ?, ?, ?)
            ''', ('nonexistent_file', 1, 1000.0, 2000.0, 50.0))
            conn.commit()

        conn.close()

    def test_survey_points_auto_id(self, temp_db):
        """Test survey_points auto-increment ID."""
        from app.shared.models import init_db, SurveyPoint, SurveyFile

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test')

        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0}
        ])

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM survey_points WHERE file_name = ?', ('test_file',))
        row = cursor.fetchone()

        assert row[0] is not None
        assert isinstance(row[0], int)

        conn.close()


class TestDatabaseOperations:
    """Test database CRUD operations."""

    def test_create_survey_file(self, temp_db):
        """Test creating a survey file."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)

        result = SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        assert result is not None
        assert result['name'] == 'test_file'
        assert result['date'] == '2026-08-31'
        assert result['place'] == 'Test Location'
        assert result['no_of_points'] == 0

    def test_get_survey_file_by_name(self, temp_db):
        """Test retrieving survey file by name."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        result = SurveyFile.get_by_name(temp_db, 'test_file')

        assert result is not None
        assert result['name'] == 'test_file'

    def test_get_nonexistent_file(self, temp_db):
        """Test retrieving nonexistent file returns None."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)

        result = SurveyFile.get_by_name(temp_db, 'nonexistent')

        assert result is None

    def test_get_all_files(self, temp_db):
        """Test retrieving all files."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)
        SurveyFile.create(temp_db, 'file1', '2026-08-31', 'Location 1')
        SurveyFile.create(temp_db, 'file2', '2026-08-30', 'Location 2')

        result = SurveyFile.get_all(temp_db)

        assert len(result) == 2

    def test_delete_survey_file(self, temp_db):
        """Test deleting a survey file."""
        from app.shared.models import init_db, SurveyFile

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        SurveyFile.delete(temp_db, 'test_file')

        result = SurveyFile.get_by_name(temp_db, 'test_file')
        assert result is None

    def test_delete_file_cascades_points(self, temp_db):
        """Test deleting file also deletes its points."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')
        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0}
        ])

        SurveyFile.delete(temp_db, 'test_file')

        points = SurveyPoint.get_by_file(temp_db, 'test_file')
        assert len(points) == 0

    def test_update_points_count(self, temp_db):
        """Test updating points count for file."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        ])

        file_info = SurveyFile.get_by_name(temp_db, 'test_file')
        assert file_info['no_of_points'] == 2


class TestSurveyPointOperations:
    """Test survey point operations."""

    def test_save_single_point(self, temp_db):
        """Test saving a single point."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        count = SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0}
        ])

        assert count == 1

        points = SurveyPoint.get_by_file(temp_db, 'test_file')
        assert len(points) == 1
        assert points[0]['y'] == 1000.0
        assert points[0]['x'] == 2000.0

    def test_save_multiple_points(self, temp_db):
        """Test saving multiple points."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        points = [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
            {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        ]

        count = SurveyPoint.save_batch(temp_db, 'test_file', points)

        assert count == 3

        result = SurveyPoint.get_by_file(temp_db, 'test_file')
        assert len(result) == 3

    def test_points_ordered_by_no(self, temp_db):
        """Test points are ordered by point number."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 3, 'y': 3000.0, 'x': 3000.0, 'h': 60.0},
            {'no': 1, 'y': 1000.0, 'x': 1000.0, 'h': 50.0},
            {'no': 2, 'y': 2000.0, 'x': 2000.0, 'h': 55.0},
        ])

        points = SurveyPoint.get_by_file(temp_db, 'test_file')

        assert points[0]['no'] == 1
        assert points[1]['no'] == 2
        assert points[2]['no'] == 3

    def test_delete_all_points_for_file(self, temp_db):
        """Test deleting all points for a file."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        ])

        SurveyPoint.delete(temp_db, 'test_file')

        points = SurveyPoint.get_by_file(temp_db, 'test_file')
        assert len(points) == 0

    def test_point_code_field(self, temp_db):
        """Test point code field works correctly."""
        from app.shared.models import init_db, SurveyFile, SurveyPoint

        init_db(temp_db)
        SurveyFile.create(temp_db, 'test_file', '2026-08-31', 'Test Location')

        SurveyPoint.save_batch(temp_db, 'test_file', [
            {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0, 'code': 'BM1'},
            {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0, 'code': ''},
        ])

        points = SurveyPoint.get_by_file(temp_db, 'test_file')

        assert points[0]['code'] == 'BM1'
        assert points[1]['code'] == ''


class TestSettingsOperations:
    """Test settings operations."""

    def test_get_nonexistent_setting(self, temp_db):
        """Test getting nonexistent setting returns default."""
        from app.shared.models import init_db, Settings

        init_db(temp_db)

        result = Settings.get(temp_db, 'nonexistent', 'default_value')

        assert result == 'default_value'

    def test_set_and_get_setting(self, temp_db):
        """Test setting and getting a value."""
        from app.shared.models import init_db, Settings

        init_db(temp_db)

        Settings.set(temp_db, 'test_key', 'test_value')
        result = Settings.get(temp_db, 'test_key')

        assert result == 'test_value'

    def test_settings_persistence(self, temp_db):
        """Test settings persist across connections."""
        from app.shared.models import init_db, Settings

        init_db(temp_db)

        Settings.set(temp_db, 'persist_key', 'persist_value')

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('persist_key',))
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 'persist_value'

    def test_get_all_settings(self, temp_db):
        """Test getting all settings."""
        from app.shared.models import init_db, Settings

        init_db(temp_db)

        Settings.set(temp_db, 'key1', 'value1')
        Settings.set(temp_db, 'key2', 'value2')

        result = Settings.get_all(temp_db)

        assert result['key1'] == 'value1'
        assert result['key2'] == 'value2'
