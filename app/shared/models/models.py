"""
Database models and initialization for MAS application.
"""
import sqlite3
from contextlib import contextmanager


def get_db_connection(db_path):
    """
    Create a database connection with row factory.
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        sqlite3.Connection object with row_factory set
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path):
    """
    Context manager for database access.
    
    Args:
        db_path: Path to SQLite database file
    
    Yields:
        sqlite3.Connection object
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path):
    """
    Initialize database with required tables.
    
    Args:
        db_path: Path to SQLite database file
    """
    with get_db(db_path) as db:
        # Survey files table
        db.execute('''
            CREATE TABLE IF NOT EXISTS survey_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                date TEXT,
                place TEXT,
                notes TEXT,
                no_of_points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Survey points table
        db.execute('''
            CREATE TABLE IF NOT EXISTS survey_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                point_no INTEGER NOT NULL,
                y REAL DEFAULT 0,
                x REAL DEFAULT 0,
                h REAL DEFAULT 0,
                code TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES survey_files(id) ON DELETE CASCADE,
                UNIQUE(file_id, point_no)
            )
        ''')
        
        # Settings table
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Default settings
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('angle_unit', 'GRADS')
        ''')
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('vertical_angle', 'GRADS')
        ''')
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printing', 'YES')
        ''')
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('company_name', 'Alrafideen Surveying Office')
        ''')
        db.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('phone', '0562150193')
        ''')


class SurveyFile:
    """Survey file model."""
    
    @staticmethod
    def get_all(db_path):
        """Get all survey files ordered by date."""
        with get_db(db_path) as db:
            rows = db.execute(
                'SELECT * FROM survey_files ORDER BY created_at DESC'
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_name(db_path, name):
        """Get survey file by name."""
        with get_db(db_path) as db:
            row = db.execute(
                'SELECT * FROM survey_files WHERE name = ?', (name,)
            ).fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def create(db_path, name, date=None, place=None, notes=None):
        """Create a new survey file."""
        with get_db(db_path) as db:
            try:
                cursor = db.execute(
                    '''INSERT INTO survey_files (name, date, place, notes)
                       VALUES (?, ?, ?, ?)''',
                    (name, date, place, notes)
                )
                return {'id': cursor.lastrowid, 'name': name}
            except sqlite3.IntegrityError:
                return None
    
    @staticmethod
    def delete(db_path, name):
        """Delete a survey file and its points."""
        with get_db(db_path) as db:
            db.execute('DELETE FROM survey_files WHERE name = ?', (name,))
            return True


class SurveyPoint:
    """Survey point model."""
    
    @staticmethod
    def get_by_file(db_path, file_name):
        """Get all points for a survey file."""
        with get_db(db_path) as db:
            row = db.execute(
                'SELECT id FROM survey_files WHERE name = ?', (file_name,)
            ).fetchone()
            if not row:
                return []
            
            file_id = row['id']
            rows = db.execute(
                '''SELECT * FROM survey_points 
                   WHERE file_id = ? ORDER BY point_no''',
                (file_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_file_as_dict(db_path, file_name):
        """Get all points for a survey file as a dictionary keyed by point number."""
        with get_db(db_path) as db:
            row = db.execute(
                'SELECT id FROM survey_files WHERE name = ?', (file_name,)
            ).fetchone()
            if not row:
                return {}
            
            file_id = row['id']
            rows = db.execute(
                '''SELECT * FROM survey_points 
                   WHERE file_id = ? ORDER BY point_no''',
                (file_id,)
            ).fetchall()
            
            result = {}
            for row in rows:
                point_dict = dict(row)
                no = point_dict.get('point_no')
                if no is not None:
                    result[no] = {
                        'y': point_dict.get('y', 0),
                        'x': point_dict.get('x', 0),
                        'h': point_dict.get('h', 0)
                    }
            return result
    
    @staticmethod
    def save_batch(db_path, file_name, points):
        """
        Save a batch of points for a survey file.
        
        Args:
            db_path: Database path
            file_name: Survey file name
            points: List of point dictionaries
        
        Returns:
            Number of points saved
        """
        with get_db(db_path) as db:
            row = db.execute(
                'SELECT id FROM survey_files WHERE name = ?', (file_name,)
            ).fetchone()
            if not row:
                return 0
            
            file_id = row['id']
            
            db.execute('DELETE FROM survey_points WHERE file_id = ?', (file_id,))
            
            for p in points:
                db.execute(
                    '''INSERT INTO survey_points 
                       (file_id, point_no, y, x, h, code, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (file_id, p['no'], p.get('y', 0), p.get('x', 0), 
                     p.get('h', 0), p.get('code', ''), p.get('desc', ''))
                )
            
            db.execute(
                'UPDATE survey_files SET no_of_points = ? WHERE id = ?',
                (len(points), file_id)
            )
            
            return len(points)


class Settings:
    """Application settings model."""
    
    @staticmethod
    def get_all(db_path):
        """Get all settings as dictionary."""
        with get_db(db_path) as db:
            rows = db.execute('SELECT key, value FROM settings').fetchall()
            return {row['key']: row['value'] for row in rows}
    
    @staticmethod
    def get(db_path, key, default=None):
        """Get a single setting value."""
        with get_db(db_path) as db:
            row = db.execute(
                'SELECT value FROM settings WHERE key = ?', (key,)
            ).fetchone()
            return row['value'] if row else default
    
    @staticmethod
    def set(db_path, key, value):
        """Set a setting value."""
        with get_db(db_path) as db:
            db.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            return True
