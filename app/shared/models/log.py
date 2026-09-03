"""
System logs (admin panel).
"""
from datetime import datetime

from .base import db


class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), default='INFO', index=True)
    message = db.Column(db.Text)
    source = db.Column(db.String(200))
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
