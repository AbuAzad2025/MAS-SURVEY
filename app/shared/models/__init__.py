"""
Shared models for all programs.
Database models and utilities.
"""
import sqlite3
import os
from datetime import datetime


def get_db_connection(db_path):
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(db_path):
    """Initialize database tables."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Survey Files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_files (
            name TEXT PRIMARY KEY,
            date TEXT,
            place TEXT,
            no_of_points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Survey Points table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            no INTEGER,
            y REAL,
            x REAL,
            h REAL,
            code TEXT,
            FOREIGN KEY (file_name) REFERENCES survey_files(name) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_survey_points_file_name ON survey_points(file_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_survey_points_no ON survey_points(no)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_survey_files_created_at ON survey_files(created_at)')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


VALID_SETTINGS_KEYS = {'angle_unit', 'vertical_angle', 'printing', 'company_name', 'phone', 'address'}


class Settings:
    """Application settings."""
    
    @staticmethod
    def get(db_path, key, default=None):
        """Get a setting value."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else default
    
    @staticmethod
    def set(db_path, key, value):
        """Set a setting value."""
        if key not in VALID_SETTINGS_KEYS:
            return
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        ''', (key, str(value)))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all(db_path):
        """Get all settings as dict."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        rows = cursor.fetchall()
        conn.close()
        return {row['key']: row['value'] for row in rows}


class SurveyFile:
    """Survey file model."""
    
    @staticmethod
    def create(db_path, name, date=None, place=None):
        """Create a new survey file."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO survey_files (name, date, place) VALUES (?, ?, ?)
            ''', (name, date, place))
            conn.commit()
            result = {'name': name, 'date': date, 'place': place, 'no_of_points': 0}
        except sqlite3.IntegrityError:
            result = None
        conn.close()
        return result
    
    @staticmethod
    def get_by_name(db_path, name):
        """Get file by name."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM survey_files WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all(db_path):
        """Get all files."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM survey_files ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def delete(db_path, name):
        """Delete a file and its points."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM survey_points WHERE file_name = ?', (name,))
        cursor.execute('DELETE FROM survey_files WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_points_count(db_path, name):
        """Update points count for a file."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE survey_files 
            SET no_of_points = (
                SELECT COUNT(*) FROM survey_points WHERE file_name = ?
            )
            WHERE name = ?
        ''', (name, name))
        conn.commit()
        conn.close()


class SurveyPoint:
    """Survey point model."""
    
    @staticmethod
    def save_batch(db_path, file_name, points):
        """Save multiple points."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        for point in points:
            cursor.execute('''
                INSERT INTO survey_points (file_name, no, y, x, h, code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                file_name,
                point.get('no', 0),
                point.get('y', 0),
                point.get('x', 0),
                point.get('h', 0),
                point.get('code', '')
            ))
        
        conn.commit()
        SurveyFile.update_points_count(db_path, file_name)
        conn.close()
        return len(points)
    
    @staticmethod
    def get_by_file(db_path, file_name):
        """Get all points for a file."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM survey_points 
            WHERE file_name = ? 
            ORDER BY no
        ''', (file_name,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def delete(db_path, file_name):
        """Delete all points for a file."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM survey_points WHERE file_name = ?', (file_name,))
        conn.commit()
        conn.close()
