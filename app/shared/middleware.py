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

from flask import session, redirect, url_for, request, jsonify

from .models import db, User, Tenant, TenantUser, Role


# --- user/tenant context ------------------------------------------------

def _load_user() -> 'User | None':
    """Resolve the current user from session.

    flask.g is NOT used as a cache because it can persist across requests in
    test_client and admin shell contexts, leading to stale identity.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    try:
        user = db.session.get(User, user_id)
    except Exception:
        return None
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
        return query.filter(db.false())
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
        if user.role != Role.SUPER_ADMIN:
            return jsonify({'error': 'Super admin required'}), 403
        return f(*args, **kwargs)
    return wrapper


# --- plan / subscription guards -------------------------------------------

# No tiers: every duration is unlimited. Fail-open so a missing/empty
# plans table can never lock tenants out; tenant_block_reason still gates.
_FALLBACK_LIMITS = {'max_files': -1, 'max_points': -1, 'max_users': -1}


def get_plan_limits(plan_name) -> dict:
    """Return {max_files, max_points, max_users} for a plan name.

    Queries Plan by name+is_active. Returns unlimited fallback
    {'max_files': -1, 'max_points': -1, 'max_users': -1} on any error,
    missing Plan model, or plan not found. -1 means unlimited.
    """
    fallback = dict(_FALLBACK_LIMITS)
    try:
        from .models import Plan
    except Exception:
        return fallback
    try:
        try:
            name = str(plan_name or 'none').strip() or 'none'
        except Exception:
            name = 'none'
        plan = Plan.query.filter_by(name=name, is_active=True).first()
        if plan is None:
            try:
                from .models import seed_default_plans
                seed_default_plans()
            except Exception:
                pass
            plan = Plan.query.filter_by(name=name, is_active=True).first()
        if plan is None:
            return fallback
        return {
            'max_files': plan.max_files if plan.max_files is not None else -1,
            'max_points': plan.max_points if plan.max_points is not None else -1,
            'max_users': plan.max_users if plan.max_users is not None else -1,
        }
    except Exception:
        return fallback


def tenant_block_reason(tenant):
    """Return None if tenant may proceed, else block reason.

    Subscriptions are durations covering ALL platform programs:
    - None tenant -> 'no_tenant'
    - getattr(tenant, 'is_suspended', False) truthy -> 'suspended'
    - plan == 'unlimited' -> never expires, always allowed
    - otherwise an unexpired expires_at is required, else 'expired'
      (covers 'none'/legacy names and lapsed weekly/monthly/yearly)
    """
    try:
        if tenant is None:
            return 'no_tenant'
        if getattr(tenant, 'is_suspended', False):
            return 'suspended'
        try:
            raw_plan = getattr(tenant, 'plan', None) or 'none'
            plan_name = str(raw_plan).strip().lower() or 'none'
        except Exception:
            plan_name = 'none'
        if plan_name == 'unlimited':
            return None
        expires_at = getattr(tenant, 'expires_at', None)
        if expires_at is None:
            return 'expired'
        try:
            from datetime import datetime as _dt
            if expires_at < _dt.utcnow():
                return 'expired'
        except Exception:
            return 'expired'
        return None
    except Exception:
        return None


# --- bootstrap ----------------------------------------------------------

def ensure_super_admin() -> None:
    """Create the default super_admin user + tenant on first run."""
    from .models import db
    existing = User.query.filter_by(username='admin').first()
    if existing:
        return
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
        plan='unlimited',
        expires_at=None,
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
