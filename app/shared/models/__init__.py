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
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'guest',
            full_name TEXT,
            whatsapp_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)')
    
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


import hashlib
import secrets
from datetime import datetime


class User:
    """User model with role-based access control."""
    
    ROLES = {
        'super_admin': 'Super Admin (Full Access)',
        'registered': 'Registered User (Full Access)',
        'guest': 'Guest (Read Only)'
    }
    
    @staticmethod
    def _hash_password(password):
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{pwd_hash.hex()}"
    
    @staticmethod
    def _verify_password(password, password_hash):
        """Verify password against hash."""
        try:
            salt, pwd_hash = password_hash.split(':')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except:
            return False
    
    @staticmethod
    def create(db_path, username, password, role='guest', email=None, phone=None, full_name=None, created_by=None):
        """Create a new user."""
        if role not in User.ROLES:
            return None
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        password_hash = User._hash_password(password)
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, email, phone, full_name, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, role, email, phone, full_name, created_by))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    @staticmethod
    def authenticate(db_path, username, password):
        """Authenticate user and return user data if successful."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row and User._verify_password(password, row['password_hash']):
            user = dict(row)
            del user['password_hash']
            return user
        return None
    
    @staticmethod
    def get_by_id(db_path, user_id):
        """Get user by ID."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, phone, role, full_name, whatsapp_verified, is_active, created_at, last_login FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_username(db_path, username):
        """Get user by username."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, phone, role, full_name, whatsapp_verified, is_active, created_at, last_login FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all(db_path):
        """Get all users."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, phone, role, full_name, whatsapp_verified, is_active, created_at, last_login FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_last_login(db_path, user_id):
        """Update last login timestamp."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update(db_path, user_id, **kwargs):
        """Update user fields."""
        allowed_fields = {'email', 'phone', 'full_name', 'role', 'is_active', 'whatsapp_verified'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        set_clause = ', '.join(f'{k} = ?' for k in updates)
        values = list(updates.values()) + [user_id]
        cursor.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    @staticmethod
    def change_password(db_path, user_id, new_password):
        """Change user password."""
        password_hash = User._hash_password(new_password)
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def delete(db_path, user_id):
        """Delete user (soft delete - set is_active = 0)."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def has_permission(user, permission):
        """Check if user has specific permission."""
        role = user.get('role', 'guest')
        
        permissions = {
            'super_admin': ['*'],  # All permissions
            'registered': [
                'survey_files.read', 'survey_files.create', 'survey_files.update', 'survey_files.delete',
                'survey_points.read', 'survey_points.create', 'survey_points.update', 'survey_points.delete',
                'calculations.all', 'settings.read', 'settings.update_own'
            ],
            'guest': [
                'survey_files.read', 'survey_points.read', 'calculations.basic'
            ]
        }
        
        user_perms = permissions.get(role, [])
        if '*' in user_perms:
            return True
        return permission in user_perms


# Super Admin default credentials
SUPER_ADMIN_INFO = {
    'name': 'أبو أزاد',
    'whatsapp': '+972562150193',
    'note': 'إنشاء الحسابات يتم فقط عبر التواصل مع السوبر أدمن على الواتساب'
}
