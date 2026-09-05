"""
Owner (super-admin billing/tenants) routes.
PostgreSQL + SQLAlchemy + multi-tenant.
"""
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template, session
from sqlalchemy import func

from app.shared.models import db, User, Tenant, TenantUser, SurveyFile
from app.shared.models.billing import Plan, Subscription
from app.shared.middleware import super_admin_required, login_required, get_current_user


owner_bp = Blueprint('owner', __name__, url_prefix='/admin')


# --- helpers -----------------------------------------------------------

def _tenant_to_dict(tenant) -> dict:
    owner_username = None
    try:
        owner = getattr(tenant, 'owner', None)
        if owner is not None:
            owner_username = owner.username
        else:
            u = db.session.get(User, tenant.owner_id) if getattr(tenant, 'owner_id', None) else None
            owner_username = u.username if u else None
    except Exception:
        owner_username = None

    try:
        users_count = TenantUser.query.filter_by(tenant_id=tenant.id).count()
        if users_count == 0 and getattr(tenant, 'owner_id', None):
            users_count = 1
    except Exception:
        users_count = 0

    try:
        files_count = SurveyFile.query.filter_by(tenant_id=tenant.id).count()
    except Exception:
        files_count = 0

    try:
        total = db.session.query(func.sum(SurveyFile.no_of_points)).filter(
            SurveyFile.tenant_id == tenant.id).scalar()
        points_count = int(total or 0)
    except Exception:
        points_count = 0

    return {
        'id': tenant.id,
        'name': tenant.name,
        'owner_username': owner_username,
        'plan': getattr(tenant, 'plan', None),
        'is_suspended': bool(getattr(tenant, 'is_suspended', False)),
        'expires_at': tenant.expires_at.isoformat() if getattr(tenant, 'expires_at', None) else None,
        'users_count': users_count,
        'files_count': files_count,
        'points_count': points_count,
    }


def _subscription_to_dict(sub) -> dict:
    tenant_name = None
    try:
        t = getattr(sub, 'tenant', None)
        if t is not None and getattr(t, 'name', None):
            tenant_name = t.name
        else:
            tenant = db.session.get(Tenant, sub.tenant_id) if getattr(sub, 'tenant_id', None) else None
            tenant_name = tenant.name if tenant else None
    except Exception:
        tenant_name = None

    plan_name = None
    price = None
    try:
        p = getattr(sub, 'plan', None)
        if p is not None:
            plan_name = getattr(p, 'name', None)
            price = getattr(p, 'price', None)
        else:
            plan = db.session.get(Plan, sub.plan_id) if getattr(sub, 'plan_id', None) else None
            if plan:
                plan_name = plan.name
                price = plan.price
    except Exception:
        pass

    def _iso(v):
        return v.isoformat() if v else None

    contact = None
    try:
        from app.shared.models import User as _User
        owner_user = None
        t = getattr(sub, 'tenant', None)
        if t is not None and getattr(t, 'owner_id', None):
            owner_user = db.session.get(_User, t.owner_id)
        elif getattr(sub, 'tenant_id', None):
            tenant = db.session.get(Tenant, sub.tenant_id)
            if tenant is not None and getattr(tenant, 'owner_id', None):
                owner_user = db.session.get(_User, tenant.owner_id)
        if owner_user is not None:
            contact = {
                'username': owner_user.username,
                'full_name': owner_user.full_name,
                'email': owner_user.email,
                'phone': owner_user.phone,
                'whatsapp': getattr(owner_user, 'whatsapp', None),
            }
    except Exception:
        contact = None

    return {
        'id': sub.id,
        'tenant_id': sub.tenant_id,
        'tenant_name': tenant_name,
        'contact': contact,
        'plan_id': sub.plan_id,
        'plan_name': plan_name,
        'price': price,
        'status': sub.status,
        'start_date': _iso(getattr(sub, 'start_date', None)),
        'end_date': _iso(getattr(sub, 'end_date', None)),
        'approved_by': getattr(sub, 'approved_by', None),
        'notes': getattr(sub, 'notes', None),
        'created_at': _iso(getattr(sub, 'created_at', None)),
    }


def _plan_to_dict(plan) -> dict:
    def _iso(v):
        return v.isoformat() if v else None
    return {
        'id': plan.id,
        'name': plan.name,
        'description': getattr(plan, 'description', None),
        'price': getattr(plan, 'price', None),
        'duration_days': getattr(plan, 'duration_days', None),
        'is_active': bool(getattr(plan, 'is_active', True)),
        'created_at': _iso(getattr(plan, 'created_at', None)),
    }


def _active_sub_dict(tenant_id):
    try:
        sub = (Subscription.query.filter_by(tenant_id=tenant_id, status='active')
               .order_by(Subscription.id.desc()).first())
    except Exception:
        sub = None
    if not sub:
        return None
    plan_name = None
    try:
        plan_name = sub.plan.name if getattr(sub, 'plan', None) else None
        if plan_name is None and getattr(sub, 'plan_id', None):
            p = db.session.get(Plan, sub.plan_id)
            plan_name = p.name if p else None
    except Exception:
        pass
    return {
        'id': sub.id,
        'plan_name': plan_name,
        'status': sub.status,
        'end_date': sub.end_date.isoformat() if getattr(sub, 'end_date', None) else None,
    }


def _lazy_log(action, entity_type=None, entity_id=None, details=None, tenant_id=None):
    try:
        from app.shared.activity import log_action
        log_action(action, entity_type, entity_id, details, tenant_id=tenant_id)
    except Exception:
        pass


def _strict_bool(value):
    """Parse booleans strictly: 'false' string must not become True."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ('true', '1', 'yes'):
        return True
    if isinstance(value, str) and value.strip().lower() in ('false', '0', 'no'):
        return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return None


def _ensure_plans_seeded():
    """Re-seed default plans if the table is empty.

    The pytest session fixtures drop/recreate the schema AFTER
    create_app() has run, which wipes the seed rows. Lazy re-seeding
    here keeps the contract (weekly/monthly/yearly/unlimited present).
    """
    try:
        names = {r[0] for r in Plan.query.with_entities(Plan.name).all()}
        if not {'weekly', 'monthly', 'yearly', 'unlimited'}.issubset(names):
            from app.shared.models import seed_default_plans
            seed_default_plans()
    except Exception:
        pass


# --- pages -------------------------------------------------------------

@owner_bp.route('/tenants')
@super_admin_required
def tenants_page():
    return render_template('admin/tenants.html')


@owner_bp.route('/tenants/<int:tenant_id>')
@super_admin_required
def tenant_detail_page(tenant_id):
    if not db.session.get(Tenant, tenant_id):
        return render_template('error.html', message='Tenant not found'), 404
    return render_template('admin/tenant_detail.html')


@owner_bp.route('/subscriptions')
@super_admin_required
def subscriptions_page():
    return render_template('admin/subscriptions.html')


@owner_bp.route('/plans')
@super_admin_required
def plans_page():
    return render_template('admin/plans.html')


# --- overview / tenants APIs -------------------------------------------

@owner_bp.route('/api/overview', methods=['GET'])
@super_admin_required
def api_overview():
    try:
        tenants_total = Tenant.query.count()
    except Exception:
        tenants_total = 0
    try:
        tenants_suspended = Tenant.query.filter_by(is_suspended=True).count()
    except Exception:
        tenants_suspended = 0
    try:
        users_total = User.query.count()
    except Exception:
        users_total = 0
    try:
        files_total = SurveyFile.query.count()
    except Exception:
        files_total = 0
    try:
        total = db.session.query(func.sum(SurveyFile.no_of_points)).scalar()
        points_total = int(total or 0)
    except Exception:
        points_total = 0
    try:
        subs_pending = Subscription.query.filter_by(status='pending').count()
    except Exception:
        subs_pending = 0
    try:
        subs_active = Subscription.query.filter_by(status='active').count()
    except Exception:
        subs_active = 0
    return jsonify({
        'tenants_total': tenants_total,
        'tenants_suspended': tenants_suspended,
        'users_total': users_total,
        'files_total': files_total,
        'points_total': points_total,
        'subs_pending': subs_pending,
        'subs_active': subs_active,
    })


@owner_bp.route('/api/tenants', methods=['GET'])
@super_admin_required
def api_list_tenants():
    tenants = Tenant.query.order_by(Tenant.id.asc()).all()
    out = []
    for t in tenants:
        d = _tenant_to_dict(t)
        d['active_subscription'] = _active_sub_dict(t.id)
        out.append(d)
    return jsonify(out)


@owner_bp.route('/api/tenants/<int:tenant_id>', methods=['GET'])
@super_admin_required
def api_tenant_detail(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    tdict = _tenant_to_dict(tenant)
    tdict['active_subscription'] = _active_sub_dict(tenant.id)

    try:
        memberships = TenantUser.query.filter_by(tenant_id=tenant.id).all()
        user_ids = [m.user_id for m in memberships]
        if tenant.owner_id and tenant.owner_id not in user_ids:
            user_ids.append(tenant.owner_id)
        users = [u.to_dict() for u in User.query.filter(User.id.in_(user_ids)).all()] if user_ids else []
    except Exception:
        users = []

    try:
        files = [f.to_dict() for f in SurveyFile.query.filter_by(tenant_id=tenant.id).all()]
    except Exception:
        files = []

    try:
        subs = (Subscription.query.filter_by(tenant_id=tenant.id)
                .order_by(Subscription.created_at.desc()).all())
        subs_payload = [_subscription_to_dict(s) for s in subs]
    except Exception:
        subs_payload = []

    return jsonify({
        'tenant': tdict,
        'users': users,
        'files': files,
        'subscriptions': subs_payload,
    })


@owner_bp.route('/api/tenants/<int:tenant_id>/suspend', methods=['POST'])
@super_admin_required
def api_suspend_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    tenant.is_suspended = True
    try:
        active_subs = Subscription.query.filter_by(tenant_id=tenant.id, status='active').all()
        for s in active_subs:
            s.status = 'suspended'
    except Exception:
        pass
    db.session.commit()
    _lazy_log('tenant.suspended', 'tenant', tenant.id,
              f'tenant={tenant.name}', tenant_id=tenant.id)
    return jsonify({'status': 'ok', 'tenant': _tenant_to_dict(tenant)})


@owner_bp.route('/api/tenants/<int:tenant_id>/unsuspend', methods=['POST'])
@super_admin_required
def api_unsuspend_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    tenant.is_suspended = False
    try:
        from datetime import datetime as _dt
        now = _dt.utcnow()
        suspended_subs = Subscription.query.filter_by(tenant_id=tenant.id, status='suspended').all()
        for s in suspended_subs:
            # Only resume subscriptions that are still within their term.
            end = getattr(s, 'end_date', None)
            if end is None or end > now:
                s.status = 'active'
            else:
                s.status = 'expired'
    except Exception:
        pass
    db.session.commit()
    _lazy_log('tenant.unsuspended', 'tenant', tenant.id,
              f'tenant={tenant.name}', tenant_id=tenant.id)
    return jsonify({'status': 'ok', 'tenant': _tenant_to_dict(tenant)})


# --- subscriptions APIs ------------------------------------------------

@owner_bp.route('/api/subscriptions', methods=['GET'])
@super_admin_required
def api_list_subscriptions():
    status = (request.args.get('status') or '').strip()
    q = Subscription.query
    if status and status != 'all':
        q = q.filter_by(status=status)
    subs = q.order_by(Subscription.created_at.desc()).all()
    return jsonify([_subscription_to_dict(s) for s in subs])


@owner_bp.route('/api/subscriptions', methods=['POST'])
@super_admin_required
def api_create_subscription():
    data = request.get_json(silent=True) or {}
    try:
        tenant_id = int(data.get('tenant_id'))
        plan_id = int(data.get('plan_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'tenant_id and plan_id must be integers'}), 400
    notes = data.get('notes')
    _ensure_plans_seeded()
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    plan = db.session.get(Plan, plan_id)
    if not plan or not getattr(plan, 'is_active', True):
        return jsonify({'error': 'Plan not found or disabled'}), 404
    existing = (Subscription.query.filter_by(tenant_id=tenant.id, status='pending').first())
    if existing:
        return jsonify({'error': 'Tenant already has a pending subscription'}), 400
    sub = Subscription(tenant_id=tenant.id, plan_id=plan.id, status='pending', notes=notes)
    db.session.add(sub)
    db.session.commit()
    return jsonify({'status': 'ok', 'subscription': _subscription_to_dict(sub)})


@owner_bp.route('/api/subscriptions/<int:sub_id>/approve', methods=['POST'])
@super_admin_required
def api_approve_subscription(sub_id):
    sub = db.session.get(Subscription, sub_id)
    if not sub:
        return jsonify({'error': 'Subscription not found'}), 404
    if sub.status != 'pending':
        return jsonify({'error': 'Only pending subscriptions can be approved'}), 400
    plan = None
    try:
        plan = sub.plan
    except Exception:
        plan = None
    if plan is None:
        plan = db.session.get(Plan, sub.plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    now = datetime.utcnow()
    # duration_days=None (unlimited) -> no end date, never expires.
    raw_duration = getattr(plan, 'duration_days', 30)
    if raw_duration is None:
        end = None
    else:
        try:
            duration = int(raw_duration)
        except Exception:
            duration = None
        if duration is None or duration <= 0:
            return jsonify({'error': 'Plan duration must be positive or unlimited'}), 400
        from datetime import timedelta
        end = now + timedelta(days=duration)
    sub.status = 'active'
    sub.start_date = now
    sub.end_date = end
    user = get_current_user()
    sub.approved_by = user.id if user else session.get('user_id')
    sub.approved_at = now
    tenant = db.session.get(Tenant, sub.tenant_id)
    if tenant:
        tenant.plan = plan.name
        tenant.expires_at = end
        # Approval lifts any suspension so the tenant can proceed.
        tenant.is_suspended = False
    db.session.commit()
    _lazy_log('subscription.approved', 'subscription', sub.id,
              f'plan={plan.name}', tenant_id=sub.tenant_id)
    return jsonify({'status': 'ok', 'subscription': _subscription_to_dict(sub)})


@owner_bp.route('/api/subscriptions/<int:sub_id>/reject', methods=['POST'])
@super_admin_required
def api_reject_subscription(sub_id):
    sub = db.session.get(Subscription, sub_id)
    if not sub:
        return jsonify({'error': 'Subscription not found'}), 404
    if sub.status != 'pending':
        return jsonify({'error': 'Only pending subscriptions can be rejected'}), 400
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', data.get('notes', ''))
    if reason:
        sub.notes = reason
    sub.status = 'cancelled'
    db.session.commit()
    _lazy_log('subscription.rejected', 'subscription', sub.id,
              f'reason={reason}', tenant_id=sub.tenant_id)
    return jsonify({'status': 'ok', 'subscription': _subscription_to_dict(sub)})


@owner_bp.route('/api/subscriptions/request', methods=['POST'])
@login_required
def api_request_subscription():
    data = request.get_json(silent=True) or {}
    plan_id = data.get('plan_id')
    notes = data.get('notes')
    if not plan_id:
        return jsonify({'error': 'plan_id required'}), 400
    _ensure_plans_seeded()
    try:
        plan = db.session.get(Plan, int(plan_id))
    except (TypeError, ValueError):
        plan = None
    if not plan or not getattr(plan, 'is_active', True):
        return jsonify({'error': 'Plan not found or disabled'}), 404
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    tenant = getattr(user, 'owned_tenant', None)
    if tenant is None:
        try:
            membership = TenantUser.query.filter_by(user_id=user.id).first()
            tenant = db.session.get(Tenant, membership.tenant_id) if membership else None
        except Exception:
            tenant = None
    if tenant is None:
        return jsonify({'error': 'No tenant found for current user'}), 400
    existing = (Subscription.query.filter_by(tenant_id=tenant.id, status='pending').first())
    if existing:
        return jsonify({'error': 'Tenant already has a pending subscription'}), 400
    sub = Subscription(tenant_id=tenant.id, plan_id=plan.id, status='pending', notes=notes)
    db.session.add(sub)
    db.session.commit()
    return jsonify({'status': 'ok', 'subscription': _subscription_to_dict(sub)})


# --- plans APIs ----------------------------------------------------------

@owner_bp.route('/api/plans', methods=['GET'])
@super_admin_required
def api_list_plans():
    _ensure_plans_seeded()
    plans = Plan.query.order_by(Plan.id.asc()).all()
    return jsonify([_plan_to_dict(p) for p in plans])


@owner_bp.route('/api/plans', methods=['POST'])
@super_admin_required
def api_create_plan():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Plan name required'}), 400
    price = data.get('price', 0)
    raw_duration = data.get('duration_days', data.get('duration', 30))
    try:
        price = float(price)
    except Exception:
        return jsonify({'error': 'Invalid price'}), 400
    # Empty/missing duration means unlimited (no expiry).
    if raw_duration is None or (isinstance(raw_duration, str) and not raw_duration.strip()):
        duration_days = None
    else:
        try:
            duration_days = int(raw_duration)
        except Exception:
            return jsonify({'error': 'Invalid duration_days'}), 400
        if duration_days <= 0:
            return jsonify({'error': 'duration_days must be positive'}), 400
    if Plan.query.filter_by(name=name).first():
        return jsonify({'error': 'Plan name already exists'}), 400

    is_active = True
    if 'is_active' in data:
        is_active = _strict_bool(data.get('is_active'))
        if is_active is None:
            return jsonify({'error': 'Invalid is_active'}), 400

    plan = Plan(
        name=name,
        price=price,
        duration_days=duration_days,
        description=data.get('description'),
    )
    plan.is_active = is_active
    db.session.add(plan)
    db.session.commit()
    _lazy_log('plan.created', 'plan', plan.id, f'plan={plan.name}', tenant_id=None)
    return jsonify({'status': 'ok', 'plan': _plan_to_dict(plan)})


@owner_bp.route('/api/plans/<int:plan_id>', methods=['PUT'])
@super_admin_required
def api_update_plan(plan_id):
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return jsonify({'error': 'Plan name required'}), 400
        dup = Plan.query.filter_by(name=new_name).first()
        if dup and dup.id != plan.id:
            return jsonify({'error': 'Plan name already exists'}), 400
        plan.name = new_name
    if 'price' in data:
        try:
            plan.price = float(data.get('price'))
        except Exception:
            return jsonify({'error': 'Invalid price'}), 400
    if 'duration_days' in data:
        raw = data.get('duration_days')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            plan.duration_days = None
        else:
            try:
                plan.duration_days = int(raw)
            except Exception:
                return jsonify({'error': 'Invalid duration_days'}), 400
            if plan.duration_days <= 0:
                return jsonify({'error': 'duration_days must be positive'}), 400
    if 'description' in data:
        plan.description = data.get('description')
    if 'is_active' in data:
        coerced = _strict_bool(data.get('is_active'))
        if coerced is None:
            return jsonify({'error': 'Invalid is_active'}), 400
        plan.is_active = coerced
    db.session.commit()
    _lazy_log('plan.updated', 'plan', plan.id, f'plan={plan.name}', tenant_id=None)
    return jsonify({'status': 'ok', 'plan': _plan_to_dict(plan)})


@owner_bp.route('/api/plans/<int:plan_id>', methods=['DELETE'])
@super_admin_required
def api_delete_plan(plan_id):
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    live = Subscription.query.filter_by(plan_id=plan.id).filter(
        Subscription.status.in_(['pending', 'active', 'suspended'])).count()
    if live:
        return jsonify({'error': 'Plan has live subscriptions and cannot be retired'}), 400
    plan.is_active = False
    db.session.commit()
    return jsonify({'status': 'ok'})
