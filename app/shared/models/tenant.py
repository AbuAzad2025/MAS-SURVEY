"""
Tenant model - every user gets a tenant (workspace) of their own.
Multi-tenant with single user per tenant; team plans can be added later.
"""
from datetime import datetime

from .base import db


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    # Subscription duration: weekly/monthly/yearly/unlimited (platform-wide).
    # 'none' = no subscription yet (blocked until owner approves one).
    plan = db.Column(db.String(20), default='none')
    is_suspended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)


class TenantUser(db.Model):
    __tablename__ = 'tenant_users'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        primary_key=True)
    role = db.Column(db.String(20), default='owner')  # owner/editor/viewer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
