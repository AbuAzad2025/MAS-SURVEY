"""
Super Admin panel routes for MAS application.
User management, system settings, statistics.
"""
from flask import Blueprint, request, jsonify, session, render_template, current_app
from app.shared.models import User, User as UserModel, SurveyFile, SurveyPoint, Settings
from app.routes.auth import super_admin_required, login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@super_admin_required
def admin_dashboard():
    """Super Admin dashboard."""
    db = current_app.config['DATABASE']
    
    # Get statistics
    users = User.get_all(db)
    files = SurveyFile.get_all(db)
    
    stats = {
        'total_users': len(users),
        'super_admins': len([u for u in users if u['role'] == 'super_admin']),
        'registered_users': len([u for u in users if u['role'] == 'registered']),
        'guests': len([u for u in users if u['role'] == 'guest']),
        'active_users': len([u for u in users if u['is_active']]),
        'total_files': len(files),
        'total_points': sum(f.get('no_of_points', 0) for f in files)
    }
    
    return render_template('admin/dashboard.html', stats=stats, users=users)


@admin_bp.route('/users')
@super_admin_required
def admin_users():
    """User management page."""
    db = current_app.config['DATABASE']
    users = User.get_all(db)
    return render_template('admin/users.html', users=users)


@admin_bp.route('/api/users', methods=['GET'])
@super_admin_required
def api_list_users():
    """API: List all users."""
    db = current_app.config['DATABASE']
    users = User.get_all(db)
    return jsonify(users)


@admin_bp.route('/api/users', methods=['POST'])
@super_admin_required
def api_create_user():
    """API: Create new user (Super Admin only)."""
    db = current_app.config['DATABASE']
    data = request.json
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'registered')
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    full_name = data.get('full_name', '').strip() or None
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if role not in User.ROLES:
        return jsonify({'error': 'Invalid role'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    user_id = User.create(db, username, password, role, email, phone, full_name, session['user_id'])
    
    if not user_id:
        return jsonify({'error': 'Username or email already exists'}), 400
    
    user = User.get_by_id(db, user_id)
    return jsonify({'status': 'ok', 'user': user})


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@super_admin_required
def api_get_user(user_id):
    """API: Get user details."""
    db = current_app.config['DATABASE']
    user = User.get_by_id(db, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user)


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@super_admin_required
def api_update_user(user_id):
    """API: Update user."""
    db = current_app.config['DATABASE']
    data = request.json
    
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot modify yourself via API'}), 400
    
    success = User.update(db, user_id, **data)
    if not success:
        return jsonify({'error': 'User not found or no changes'}), 404
    
    user = User.get_by_id(db, user_id)
    return jsonify({'status': 'ok', 'user': user})


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@super_admin_required
def api_delete_user(user_id):
    """API: Delete user (soft delete)."""
    db = current_app.config['DATABASE']
    
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    User.delete(db, user_id)
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@super_admin_required
def api_reset_password(user_id):
    """API: Reset user password."""
    db = current_app.config['DATABASE']
    data = request.json
    new_password = data.get('new_password', '')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    User.change_password(db, user_id, new_password)
    return jsonify({'status': 'ok', 'message': 'Password reset successfully'})


@admin_bp.route('/api/stats', methods=['GET'])
@super_admin_required
def api_stats():
    """API: Get system statistics."""
    db = current_app.config['DATABASE']
    
    users = User.get_all(db)
    files = SurveyFile.get_all(db)
    
    stats = {
        'total_users': len(users),
        'super_admins': len([u for u in users if u['role'] == 'super_admin']),
        'registered_users': len([u for u in users if u['role'] == 'registered']),
        'guests': len([u for u in users if u['role'] == 'guest']),
        'active_users': len([u for u in users if u['is_active']]),
        'total_files': len(files),
        'total_points': sum(f.get('no_of_points', 0) for f in files)
    }
    
    return jsonify(stats)


@admin_bp.route('/settings')
@super_admin_required
def admin_settings():
    """System settings page."""
    import sys
    import os
    
    db = current_app.config['DATABASE']
    settings = Settings.get_all(db)
    
    return render_template('admin/settings.html', 
                         settings=settings,
                         db_path=db,
                         python_version=sys.version.split()[0])


@admin_bp.route('/files')
@super_admin_required
def admin_files():
    """Survey files overview."""
    db = current_app.config['DATABASE']
    files = SurveyFile.get_all(db)
    return render_template('admin/files.html', files=files)


@admin_bp.route('/logs')
@super_admin_required
def admin_logs():
    """System logs page."""
    return render_template('admin/logs.html')


@admin_bp.route('/api/logs', methods=['GET'])
@super_admin_required
def api_get_logs():
    """API: Get system logs."""
    import sqlite3
    
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level', '')
    
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if logs table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'")
    if not cursor.fetchone():
        conn.close()
        return jsonify({'logs': []})
    
    query = 'SELECT * FROM system_logs'
    params = []
    
    if level:
        query += ' WHERE level = ?'
        params.append(level)
    
    query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({'logs': [dict(row) for row in rows]})


@admin_bp.route('/api/logs', methods=['DELETE'])
@super_admin_required
def api_clear_logs():
    """API: Clear all logs."""
    import sqlite3
    
    conn = sqlite3.connect(current_app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'")
    if cursor.fetchone():
        cursor.execute('DELETE FROM system_logs')
        conn.commit()
    
    conn.close()
    return jsonify({'status': 'ok'})


def log_system_event(db_path, level, module, message, user_id=None, ip=None):
    """Log a system event."""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT NOT NULL,
            module TEXT,
            message TEXT,
            user_id INTEGER,
            ip TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level)')
    
    cursor.execute('''
        INSERT INTO system_logs (level, module, message, user_id, ip)
        VALUES (?, ?, ?, ?, ?)
    ''', (level, module, message, user_id, ip))
    
    conn.commit()
    conn.close()