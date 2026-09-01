"""
Authentication routes for MAS application.
Handles login, logout, session management.
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, current_app
from app.shared.models import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific role(s)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
            user_role = session.get('user_role', 'guest')
            if user_role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def super_admin_required(f):
    """Decorator to require super_admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
        if session.get('user_role') != 'super_admin':
            return jsonify({'error': 'Super Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('main.mas_menu'))
        return render_template('login.html')
    
    data = request.json if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = User.authenticate(current_app.config['DATABASE'], username, password)
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['user_role'] = user['role']
    session['user_name'] = user['full_name'] or user['username']
    
    User.update_last_login(current_app.config['DATABASE'], user['id'])
    
    return jsonify({
        'status': 'ok',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'full_name': user['full_name']
        },
        'redirect': url_for('main.mas_menu')
    })


@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Logout handler."""
    session.clear()
    return jsonify({'status': 'ok', 'redirect': url_for('auth.login')})


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info."""
    user = User.get_by_id(current_app.config['DATABASE'], session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password for current user."""
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new password required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    user = User.authenticate(current_app.config['DATABASE'], session['username'], old_password)
    
    if not user:
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    User.change_password(current_app.config['DATABASE'], session['user_id'], new_password)
    
    return jsonify({'status': 'ok', 'message': 'Password changed successfully'})


@auth_bp.route('/super-admin-info', methods=['GET'])
def super_admin_info():
    """Get Super Admin contact info for account creation."""
    from app.shared.models import SUPER_ADMIN_INFO
    return jsonify(SUPER_ADMIN_INFO)


def init_default_super_admin(db_path):
    """Initialize default super admin if none exists."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE role = ?', ('super_admin',))
    count = cursor.fetchone()['count']
    conn.close()
    
    if count == 0:
        User.create(
            db_path,
            username='admin',
            password='admin123',  # Should be changed on first login
            role='super_admin',
            full_name='أبو أزاد (Super Admin)',
            email='admin@mas.local'
        )
        print("Default Super Admin created: admin / admin123")


def get_db_connection(db_path):
    """Get database connection."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn