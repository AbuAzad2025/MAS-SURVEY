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
            return redirect(url_for('landing.index'))
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

    # Platform entry: blocked tenants land in waiting room, everyone else
    # lands on the platform landing (program list), never inside one program.
    from app.shared.middleware import tenant_block_reason
    target = ('landing.waiting' if tenant_block_reason(user.owned_tenant)
              else 'landing.index')

    return jsonify({
        'status': 'ok',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'full_name': user.full_name,
        },
        'redirect': url_for(target),
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


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Public self-signup: contact info + package choice + subscription request.

    Creates user (registered) + tenant (plan 'none') + pending Subscription.
    The platform owner approves/rejects from /admin/subscriptions after
    external correspondence. No login required.
    """
    from app.shared.models import Tenant, TenantUser, Plan, Subscription

    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('landing.index'))
        plans = Plan.query.filter_by(is_active=True).all()
        return render_template(
            'register.html',
            plans=[{'id': p.id, 'name': p.name,
                    'description': p.description,
                    'duration_days': p.duration_days} for p in plans],
            owner=SUPER_ADMIN_INFO,
        )

    data = request.json if request.is_json else request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip() or None
    email = (data.get('email') or '').strip() or None
    phone = (data.get('phone') or '').strip() or None
    whatsapp = (data.get('whatsapp') or '').strip() or None
    plan_id = data.get('plan_id')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    if email and User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    plan = None
    if plan_id not in (None, ''):
        try:
            plan = Plan.query.filter_by(id=int(plan_id), is_active=True).first()
        except (TypeError, ValueError):
            plan = None
        if not plan:
            return jsonify({'error': 'Selected package is not available'}), 400

    user = User(username=username, email=email, phone=phone, whatsapp=whatsapp,
                role=Role.REGISTERED, full_name=full_name, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    tenant = Tenant(owner_id=user.id, name=username, plan='none', expires_at=None)
    db.session.add(tenant)
    db.session.flush()
    db.session.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role='owner'))

    if plan:
        db.session.add(Subscription(tenant_id=tenant.id, plan_id=plan.id,
                                    status='pending'))
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'message': 'Account created. Your subscription request is pending owner approval.',
        'redirect': url_for('auth.login'),
    })
