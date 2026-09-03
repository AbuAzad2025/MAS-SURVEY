"""
Survey models - tenant-scoped business data.
Every row is tied to a tenant; queries must always be filtered by tenant_id.
"""
from datetime import datetime

from .base import db


class SurveyFile(db.Model):
    __tablename__ = 'survey_files'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20))
    place = db.Column(db.String(200))
    notes = db.Column(db.Text)
    no_of_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    points = db.relationship('SurveyPoint', backref='file', lazy=True,
                             cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'name', name='unique_file_per_tenant'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'date': self.date,
            'place': self.place,
            'notes': self.notes,
            'no_of_points': self.no_of_points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SurveyPoint(db.Model):
    __tablename__ = 'survey_points'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    file_id = db.Column(db.Integer, db.ForeignKey('survey_files.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    point_no = db.Column(db.Integer, nullable=False, index=True)
    y = db.Column(db.Float, default=0)
    x = db.Column(db.Float, default=0)
    h = db.Column(db.Float, default=0)
    code = db.Column(db.String(50))
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('file_id', 'point_no', name='unique_point_per_file'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'file_id': self.file_id,
            'point_no': self.point_no,
            'no': self.point_no,  # legacy alias used by tests/API
            'y': self.y,
            'x': self.x,
            'h': self.h,
            'code': self.code or '',
            'description': self.description or '',
        }
