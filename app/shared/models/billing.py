"""
Billing models - plans, subscriptions, activity log.
"""
from datetime import datetime

from .base import db


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    duration_days = db.Column(db.Integer, default=30)
    max_files = db.Column(db.Integer, default=5)
    max_points = db.Column(db.Integer, default=500)
    max_users = db.Column(db.Integer, default=1)  # -1 = unlimited
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          index=True, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending/active/cancelled/expired/suspended
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = db.relationship('Tenant', backref='subscriptions')
    plan = db.relationship('Plan')


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True, index=True)
    action = db.Column(db.String(80), index=True)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


#: Subscription durations. One subscription covers ALL platform programs
#: (MAS, INHERITANCE, ...). No tiers, no payment - manual approval only.
#: duration_days=None means never expires. All caps are -1 (unlimited).
DURATIONS = ('weekly', 'monthly', 'yearly', 'unlimited')

#: Legacy tier names from the first version - deactivated on sight.
LEGACY_PLANS = ('free', 'pro', 'enterprise')


def seed_default_plans():
    defaults = [
        dict(name='weekly', description='Weekly subscription - all programs',
             price=0, duration_days=7,
             max_files=-1, max_points=-1, max_users=-1),
        dict(name='monthly', description='Monthly subscription - all programs',
             price=0, duration_days=30,
             max_files=-1, max_points=-1, max_users=-1),
        dict(name='yearly', description='Yearly subscription - all programs',
             price=0, duration_days=365,
             max_files=-1, max_points=-1, max_users=-1),
        dict(name='unlimited', description='Unlimited subscription - all programs',
             price=0, duration_days=None,
             max_files=-1, max_points=-1, max_users=-1),
    ]
    try:
        existing = {p.name for p in Plan.query.with_entities(Plan.name).all()}
    except Exception:
        existing = set()
    missing = [d for d in defaults if d['name'] not in existing]
    try:
        if missing:
            db.session.add_all([Plan(**d) for d in missing])
            db.session.flush()
        # Column default=30 would coerce an explicit None on INSERT;
        # force unlimited back to NULL with an UPDATE (no defaults apply).
        db.session.query(Plan).filter_by(name='unlimited').update(
            {'duration_days': None}, synchronize_session=False)
        # Retire legacy tier plans so they can no longer be assigned.
        legacy = Plan.query.filter(Plan.name.in_(LEGACY_PLANS),
                                   Plan.is_active.is_(True)).all()
        for plan in legacy:
            plan.is_active = False
        # Migrate tenants off legacy names (enterprise -> unlimited).
        from .tenant import Tenant
        for tenant in Tenant.query.filter_by(plan='enterprise').all():
            tenant.plan = 'unlimited'
            tenant.expires_at = None
        db.session.commit()
    except Exception:
        db.session.rollback()
