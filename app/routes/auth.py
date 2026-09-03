"""
Authentication routes for MAS application.
PostgreSQL + SQLAlchemy. login_required/super_admin_required live in
app.shared.middleware and are re-exported here for backwards compatibility.
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime

from app.shared.models import db, User, Role
from app.shared.middleware import (
    login_required,
    super_admin_required,
    get_current_user,
    SUPER_ADMIN_INFO,
)

__all__ = ['auth_bp', 'login_required', 'super_admin_required']


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('main.mas_menu'))
        return render_template('login.html')

    data = request.json if request.is_json else request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=username, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = user.role
    session['user_name'] = user.full_name or user.username
    session['tenant_id'] = user.owned_tenant.id if user.owned_tenant else None

    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'full_name': user.full_name,
        },
        'redirect': url_for('main.mas_menu'),
    })


@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Logout handler."""
    session.clear()
    return jsonify({'status': 'ok', 'redirect': url_for('auth.login')})


@auth_bp.route('/me', methods=['GET'])
@login_required
def current_user_info():
    """Get current user info."""
    user = get_current_user()
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password for current user."""
    data = request.json or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': 'Old and new password required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user = get_current_user()
    if not user or not user.check_password(old_password):
        return jsonify({'error': 'Current password is incorrect'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': 'Password changed successfully'})


@auth_bp.route('/super-admin-info', methods=['GET'])
def super_admin_info():
    """Public info for new account signup."""
    return jsonify(SUPER_ADMIN_INFO)
