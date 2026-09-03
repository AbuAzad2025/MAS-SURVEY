"""
User model with role-based access control.
Every user owns one tenant (multi-tenant single-user-per-tenant).
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from .base import db
from .role import Role


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default=Role.REGISTERED, nullable=False)
    full_name = db.Column(db.String(120))
    whatsapp_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Each user owns exactly one tenant (1:1)
    owned_tenant = db.relationship(
        'Tenant', backref='owner', uselist=False,
        foreign_keys='Tenant.owner_id', cascade='all, delete-orphan'
    )
    memberships = db.relationship('TenantUser', backref='user', lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'full_name': self.full_name,
            'whatsapp_verified': self.whatsapp_verified,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
