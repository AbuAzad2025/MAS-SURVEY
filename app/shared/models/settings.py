"""
Settings model - simple key/value store, tenant-scoped.
"""
from .base import db


VALID_SETTINGS_KEYS = {
    'angle_unit', 'vertical_angle', 'printing',
    'company_name', 'phone', 'address',
}


class Settings(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'key', name='unique_setting_per_tenant'),
    )

    @classmethod
    def get(cls, tenant_id: int, key: str, default=None):
        row = cls.query.filter_by(tenant_id=tenant_id, key=key).first()
        return row.value if row else default

    @classmethod
    def set(cls, tenant_id: int, key: str, value) -> bool:
        if key not in VALID_SETTINGS_KEYS:
            return False
        row = cls.query.filter_by(tenant_id=tenant_id, key=key).first()
        if row:
            row.value = str(value)
        else:
            row = cls(tenant_id=tenant_id, key=key, value=str(value))
            db.session.add(row)
        db.session.commit()
        return True

    @classmethod
    def get_all(cls, tenant_id: int) -> dict:
        rows = cls.query.filter_by(tenant_id=tenant_id).all()
        return {r.key: r.value for r in rows}
