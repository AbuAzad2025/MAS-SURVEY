"""
Auth + tenant middleware.

Two decorators that every protected route uses:

  @login_required          -> ensure user is signed in
  @super_admin_required    -> ensure role == 'super_admin'

Plus helpers for tenant-scoped queries:

  get_current_user()       -> User object (or None)
  get_current_tenant()     -> Tenant object (or None)
  tenant_scope(query)      -> apply WHERE tenant_id = ?
"""
from functools import wraps

from flask import g, session, redirect, url_for, request, jsonify

from .models import User, Tenant, TenantUser, Role


# --- user/tenant context ------------------------------------------------

def _load_user() -> 'User | None':
    """Resolve the current user from session.

    flask.g is NOT used as a cache because it can persist across requests in
    test_client and admin shell contexts, leading to stale identity.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = User.query.get(user_id)
    if user and not user.is_active:
        session.clear()
        return None
    return user


def _load_tenant() -> 'Tenant | None':
    user = _load_user()
    if user is None:
        return None
    return user.owned_tenant


def get_current_user() -> 'User | None':
    return _load_user()


def get_current_tenant() -> 'Tenant | None':
    return _load_tenant()


def tenant_scope(query):
    """Filter any SQLAlchemy query by current tenant. Empty if not signed in."""
    tenant = _load_tenant()
    if tenant is None:
        return query.filter('1=0')
    return query.filter_by(tenant_id=tenant.id)


# --- decorators ---------------------------------------------------------

def login_required(f):
    """Require authenticated user. Returns 401 for API endpoints, redirect for pages."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _load_user() is None:
            if _is_api_request():
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def _is_api_request() -> bool:
    return (request.path.startswith('/api/') or '/api/' in request.path
            or request.path.startswith('/auth/') or request.is_json)


def super_admin_required(f):
    """Require super_admin role. 401 JSON for API when anonymous, else redirect/403."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _load_user()
        if user is None:
            if _is_api_request():
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.path))
            return redirect(url_for('auth.login', next=request.path))
        if user.role != Role.SUPER_ADMIN:
            return jsonify({'error': 'Super admin required'}), 403
        return f(*args, **kwargs)
    return wrapper


# --- bootstrap ----------------------------------------------------------

def ensure_super_admin() -> None:
    """Create the default super_admin user + tenant on first run."""
    from .models import db
    existing = User.query.filter_by(username='admin').first()
    if existing:
        return
    from datetime import datetime, timedelta
    user = User(
        username='admin',
        email='admin@mas-survey.local',
        role=Role.SUPER_ADMIN,
        full_name='Super Admin',
        is_active=True,
        whatsapp_verified=True,
    )
    user.set_password('admin123')
    db.session.add(user)
    db.session.flush()
    tenant = Tenant(
        owner_id=user.id,
        name='admin',
        plan='enterprise',
        expires_at=datetime.utcnow() + timedelta(days=3650),
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role='owner'))
    db.session.commit()


# Super admin info for /auth/super-admin-info
SUPER_ADMIN_INFO = {
    'name': 'أبو أزاد',
    'whatsapp': '+972562150193',
    'note': 'إنشاء الحسابات يتم فقط عبر التواصل مع السوبر أدمن على الواتساب',
}
