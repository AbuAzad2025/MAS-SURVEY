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


def seed_default_plans():
    defaults = [
        dict(name='free', description='Free plan', price=0,
             duration_days=30, max_files=5, max_points=500, max_users=1),
        dict(name='pro', description='Pro plan', price=49,
             duration_days=365, max_files=100, max_points=50000, max_users=5),
        dict(name='enterprise', description='Enterprise plan', price=199,
             duration_days=365, max_files=-1, max_points=-1, max_users=20),
    ]
    try:
        existing = {p.name for p in Plan.query.with_entities(Plan.name).all()}
    except Exception:
        existing = set()
    missing = [d for d in defaults if d['name'] not in existing]
    if missing:
        db.session.add_all([Plan(**d) for d in missing])
        db.session.commit()
