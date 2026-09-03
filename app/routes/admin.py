"""
Super Admin panel routes.
PostgreSQL + SQLAlchemy + multi-tenant.
"""
import sys
import os
from flask import Blueprint, request, jsonify, session, render_template

from app.shared.models import db, User, Role, Tenant, SurveyFile, SystemLog
from app.shared.middleware import super_admin_required


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# --- helpers -----------------------------------------------------------

def _stats_payload() -> dict:
    users = User.query.all()
    files = SurveyFile.query.all()
    return {
        'total_users': len(users),
        'super_admins': sum(1 for u in users if u.role == Role.SUPER_ADMIN),
        'registered_users': sum(1 for u in users if u.role == Role.REGISTERED),
        'guests': sum(1 for u in users if u.role == Role.GUEST),
        'active_users': sum(1 for u in users if u.is_active),
        'total_files': len(files),
        'total_points': sum(f.no_of_points or 0 for f in files),
    }


# --- dashboard & pages -------------------------------------------------

@admin_bp.route('/')
@super_admin_required
def admin_dashboard():
    """Super Admin dashboard."""
    users = [u.to_dict() for u in User.query.all()]
    return render_template('admin/dashboard.html',
                           stats=_stats_payload(), users=users)


@admin_bp.route('/users')
@super_admin_required
def admin_users():
    """User management page."""
    users = [u.to_dict() for u in User.query.all()]
    return render_template('admin/users.html', users=users)


@admin_bp.route('/settings')
@super_admin_required
def admin_settings():
    """System settings page."""
    db_url = str(db.engine.url)
    return render_template('admin/settings.html',
                           settings={},
                           db_path=db_url,
                           python_version=sys.version.split()[0])


@admin_bp.route('/files')
@super_admin_required
def admin_files():
    """Survey files overview."""
    files = SurveyFile.query.order_by(SurveyFile.created_at.desc()).all()
    payload = []
    for f in files:
        d = f.to_dict()
        owner_username = None
        try:
            tenant = db.session.get(Tenant, f.tenant_id)
            if tenant is not None and getattr(tenant, 'owner_id', None):
                owner = db.session.get(User, tenant.owner_id)
                owner_username = owner.username if owner else None
        except Exception:
            owner_username = None
        d['owner_username'] = owner_username
        payload.append(d)
    return render_template('admin/files.html', files=payload)


@admin_bp.route('/logs')
@super_admin_required
def admin_logs():
    return render_template('admin/logs.html')


# --- users API ---------------------------------------------------------

@admin_bp.route('/api/users', methods=['GET'])
@super_admin_required
def api_list_users():
    return jsonify([u.to_dict() for u in User.query.all()])


@admin_bp.route('/api/users', methods=['POST'])
@super_admin_required
def api_create_user():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role') or Role.REGISTERED
    email = (data.get('email') or '').strip() or None
    phone = (data.get('phone') or '').strip() or None
    whatsapp = (data.get('whatsapp') or '').strip() or None
    full_name = (data.get('full_name') or '').strip() or None

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if not Role.is_valid(role):
        return jsonify({'error': 'Invalid role'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    if email and User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    user = User(
        username=username, email=email, phone=phone, whatsapp=whatsapp,
        role=role, full_name=full_name, is_active=True,
        created_by=session.get('user_id'),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # No subscription yet: tenant stays blocked until the owner
    # approves one (weekly/monthly/yearly/unlimited) via /admin/subscriptions.
    from app.shared.models import Tenant, TenantUser
    tenant = Tenant(
        owner_id=user.id, name=username, plan='none',
        expires_at=None,
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role='owner'))
    db.session.commit()

    return jsonify({'status': 'ok', 'user': user.to_dict()})


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@super_admin_required
def api_get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@super_admin_required
def api_update_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot modify yourself via API'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.json or {}
    for field in ('email', 'phone', 'full_name', 'role', 'is_active', 'whatsapp_verified'):
        if field in data:
            value = data[field]
            if field == 'role' and not Role.is_valid(value):
                return jsonify({'error': 'Invalid role'}), 400
            setattr(user, field, value)
    db.session.commit()
    return jsonify({'status': 'ok', 'user': user.to_dict()})


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@super_admin_required
def api_delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.is_active = False
    db.session.commit()
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@super_admin_required
def api_reset_password(user_id):
    data = request.json or {}
    new_password = data.get('new_password') or ''
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': 'Password reset successfully'})


@admin_bp.route('/api/stats', methods=['GET'])
@super_admin_required
def api_stats():
    return jsonify(_stats_payload())


# --- logs API ----------------------------------------------------------

@admin_bp.route('/api/logs', methods=['GET'])
@super_admin_required
def api_get_logs():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level', '').strip()

    q = SystemLog.query
    if level:
        q = q.filter_by(level=level)
    rows = q.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()
    return jsonify({'logs': [
        {
            'id': r.id,
            'level': r.level,
            'message': r.message,
            'source': r.source,
            'tenant_id': r.tenant_id,
            'user_id': r.user_id,
            'timestamp': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]})


@admin_bp.route('/api/logs', methods=['DELETE'])
@super_admin_required
def api_clear_logs():
    SystemLog.query.delete()
    db.session.commit()
    return jsonify({'status': 'ok'})
