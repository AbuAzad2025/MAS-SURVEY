"""
Database consistency and schema tests.
PostgreSQL + SQLAlchemy + tenant-scoped.
"""
import time
import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError


def _make_tenant(app):
    """Create an isolated user+tenant for a test. Returns (user_id, tenant_id)."""
    from app.shared.models import db, User, Role, Tenant, TenantUser
    from datetime import datetime, timedelta
    tag = f"t_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    with app.app_context():
        u = User(username=f"u_{tag}", email=f"{tag}@t.com",
                 role=Role.REGISTERED, is_active=True)
        u.set_password("pw12345")
        db.session.add(u)
        db.session.flush()
        t = Tenant(owner_id=u.id, name=f"tenant_{tag}", plan="free",
                   expires_at=datetime.utcnow() + timedelta(days=3650))
        db.session.add(t)
        db.session.flush()
        db.session.add(TenantUser(tenant_id=t.id, user_id=u.id, role="owner"))
        db.session.commit()
        return u.id, t.id


def _drop_tenant(app, user_id, tenant_id):
    from app.shared.models import db, User, Tenant, SurveyFile
    with app.app_context():
        for f in SurveyFile.query.filter_by(tenant_id=tenant_id).all():
            db.session.delete(f)
        t = Tenant.query.get(tenant_id)
        if t:
            db.session.delete(t)
        u = User.query.get(user_id)
        if u:
            db.session.delete(u)
        db.session.commit()


class TestDatabaseSchema:
    """Test database schema."""

    def test_database_init_creates_tables(self, app):
        from app.shared.models import db
        with app.app_context():
            tables = inspect(db.engine).get_table_names()
        for t in ('survey_files', 'survey_points', 'settings',
                  'users', 'tenants', 'tenant_users', 'system_logs'):
            assert t in tables

    def test_survey_files_table_schema(self, app):
        from app.shared.models import db
        with app.app_context():
            cols = {c['name']: str(c['type']) for c in
                    inspect(db.engine).get_columns('survey_files')}
        assert 'name' in cols and 'VARCHAR' in cols['name']
        assert 'date' in cols
        assert 'place' in cols
        assert 'no_of_points' in cols and 'INTEGER' in cols['no_of_points']
        assert 'tenant_id' in cols and 'INTEGER' in cols['tenant_id']

    def test_survey_points_table_schema(self, app):
        from app.shared.models import db
        with app.app_context():
            cols = {c['name']: str(c['type']) for c in
                    inspect(db.engine).get_columns('survey_points')}
        assert 'file_id' in cols and 'INTEGER' in cols['file_id']
        assert 'point_no' in cols and 'INTEGER' in cols['point_no']
        # PostgreSQL reports Float as DOUBLE PRECISION
        for col in ('y', 'x', 'h'):
            assert col in cols and ('FLOAT' in cols[col] or 'DOUBLE' in cols[col])
        assert 'code' in cols
        assert 'tenant_id' in cols

    def test_survey_files_primary_key(self, app):
        from app.shared.models import db
        with app.app_context():
            pk = inspect(db.engine).get_pk_constraint('survey_files')
        assert 'id' in pk['constrained_columns']

    def test_survey_points_foreign_key(self, app):
        from app.shared.models import db
        with app.app_context():
            fks = inspect(db.engine).get_foreign_keys('survey_points')
        targets = {tuple(fk['referred_columns']) for fk in fks}
        assert ('id',) in targets


class TestDatabaseConstraints:
    """Test database constraints."""

    def test_survey_file_name_unique_per_tenant(self, app):
        from app.shared.models import db, SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyFile(tenant_id=tid, name='dup', date='2026-08-31', place='L1'))
                db.session.commit()
                db.session.add(SurveyFile(tenant_id=tid, name='dup', date='2026-08-31', place='L2'))
                with pytest.raises(IntegrityError):
                    db.session.commit()
                db.session.rollback()
        finally:
            _drop_tenant(app, uid, tid)

    def test_same_name_allowed_across_tenants(self, app):
        from app.shared.models import db, SurveyFile
        uid1, tid1 = _make_tenant(app)
        uid2, tid2 = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyFile(tenant_id=tid1, name='shared'))
                db.session.add(SurveyFile(tenant_id=tid2, name='shared'))
                db.session.commit()
                n = SurveyFile.query.filter_by(name='shared').count()
                assert n == 2
        finally:
            _drop_tenant(app, uid1, tid1)
            _drop_tenant(app, uid2, tid2)

    def test_survey_points_require_file(self, app):
        from app.shared.models import db, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyPoint(tenant_id=tid, file_id=999999999,
                                           point_no=1, y=1000.0, x=2000.0, h=50.0))
                with pytest.raises(IntegrityError):
                    db.session.commit()
                db.session.rollback()
        finally:
            _drop_tenant(app, uid, tid)

    def test_survey_points_auto_id(self, app):
        from app.shared.models import db, SurveyFile, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                f = SurveyFile(tenant_id=tid, name='f', date='2026-08-31', place='T')
                db.session.add(f)
                db.session.flush()
                p = SurveyPoint(tenant_id=tid, file_id=f.id, point_no=1,
                                y=1000.0, x=2000.0, h=50.0)
                db.session.add(p)
                db.session.commit()
                assert p.id is not None and isinstance(p.id, int)
        finally:
            _drop_tenant(app, uid, tid)


class TestDatabaseOperations:
    """Test database CRUD operations."""

    def test_create_survey_file(self, app):
        from app.shared.models import db, SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                f = SurveyFile(tenant_id=tid, name='test_file',
                               date='2026-08-31', place='Test Location')
                db.session.add(f)
                db.session.commit()
                assert f.id is not None
                assert f.name == 'test_file'
                assert f.date == '2026-08-31'
                assert f.place == 'Test Location'
                assert (f.no_of_points or 0) == 0
        finally:
            _drop_tenant(app, uid, tid)

    def test_get_survey_file_by_name(self, app):
        from app.shared.models import db, SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyFile(tenant_id=tid, name='test_file',
                                          date='2026-08-31', place='Test Location'))
                db.session.commit()
                r = SurveyFile.query.filter_by(tenant_id=tid, name='test_file').first()
                assert r is not None and r.name == 'test_file'
        finally:
            _drop_tenant(app, uid, tid)

    def test_get_nonexistent_file(self, app):
        from app.shared.models import SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                r = SurveyFile.query.filter_by(tenant_id=tid, name='nonexistent').first()
                assert r is None
        finally:
            _drop_tenant(app, uid, tid)

    def test_get_all_files(self, app):
        from app.shared.models import db, SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyFile(tenant_id=tid, name='file1', date='2026-08-31', place='L1'))
                db.session.add(SurveyFile(tenant_id=tid, name='file2', date='2026-08-30', place='L2'))
                db.session.commit()
                rows = SurveyFile.query.filter_by(tenant_id=tid).all()
                assert len(rows) == 2
        finally:
            _drop_tenant(app, uid, tid)

    def test_delete_survey_file(self, app):
        from app.shared.models import db, SurveyFile
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                db.session.add(SurveyFile(tenant_id=tid, name='test_file',
                                          date='2026-08-31', place='Test Location'))
                db.session.commit()
                f = SurveyFile.query.filter_by(tenant_id=tid, name='test_file').first()
                db.session.delete(f)
                db.session.commit()
                assert SurveyFile.query.filter_by(tenant_id=tid, name='test_file').first() is None
        finally:
            _drop_tenant(app, uid, tid)

    def test_delete_file_cascades_points(self, app):
        from app.shared.models import db, SurveyFile, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                f = SurveyFile(tenant_id=tid, name='test_file', date='2026-08-31', place='T')
                db.session.add(f)
                db.session.flush()
                db.session.add(SurveyPoint(tenant_id=tid, file_id=f.id, point_no=1,
                                           y=1000.0, x=2000.0, h=50.0))
                db.session.commit()
                db.session.delete(f)
                db.session.commit()
                assert SurveyPoint.query.filter_by(file_id=f.id).count() == 0
        finally:
            _drop_tenant(app, uid, tid)

    def test_update_points_count(self, app):
        from app.shared.models import db, SurveyFile, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                f = SurveyFile(tenant_id=tid, name='test_file', date='2026-08-31', place='T')
                db.session.add(f)
                db.session.flush()
                for i, (y, x, h) in enumerate([(1000.0, 2000.0, 50.0), (1100.0, 2000.0, 55.0)], start=1):
                    db.session.add(SurveyPoint(tenant_id=tid, file_id=f.id,
                                               point_no=i, y=y, x=x, h=h))
                f.no_of_points = 2
                db.session.commit()
                assert SurveyFile.query.filter_by(tenant_id=tid, name='test_file').first().no_of_points == 2
        finally:
            _drop_tenant(app, uid, tid)


class TestSurveyPointOperations:
    """Test survey point operations."""

    def _seed(self, app, tid, name, points):
        from app.shared.models import db, SurveyFile, SurveyPoint
        with app.app_context():
            f = SurveyFile(tenant_id=tid, name=name, date='2026-08-31', place='T')
            db.session.add(f)
            db.session.flush()
            for p in points:
                db.session.add(SurveyPoint(tenant_id=tid, file_id=f.id,
                                           point_no=p['no'], y=p.get('y', 0),
                                           x=p.get('x', 0), h=p.get('h', 0),
                                           code=p.get('code', '')))
            db.session.commit()
            return f.id

    def test_save_single_point(self, app):
        from app.shared.models import db, SurveyFile, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            fid = self._seed(app, tid, 'test_file',
                             [{'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0}])
            with app.app_context():
                rows = SurveyPoint.query.filter_by(file_id=fid).all()
                assert len(rows) == 1
                assert rows[0].y == 1000.0 and rows[0].x == 2000.0
        finally:
            _drop_tenant(app, uid, tid)

    def test_save_multiple_points(self, app):
        from app.shared.models import SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            fid = self._seed(app, tid, 'test_file', [
                {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
                {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
                {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
            ])
            with app.app_context():
                assert SurveyPoint.query.filter_by(file_id=fid).count() == 3
        finally:
            _drop_tenant(app, uid, tid)

    def test_points_ordered_by_no(self, app):
        from app.shared.models import SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            fid = self._seed(app, tid, 'test_file', [
                {'no': 3, 'y': 3000.0, 'x': 3000.0, 'h': 60.0},
                {'no': 1, 'y': 1000.0, 'x': 1000.0, 'h': 50.0},
                {'no': 2, 'y': 2000.0, 'x': 2000.0, 'h': 55.0},
            ])
            with app.app_context():
                rows = SurveyPoint.query.filter_by(file_id=fid).order_by(SurveyPoint.point_no).all()
                assert [r.point_no for r in rows] == [1, 2, 3]
        finally:
            _drop_tenant(app, uid, tid)

    def test_delete_all_points_for_file(self, app):
        from app.shared.models import db, SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            fid = self._seed(app, tid, 'test_file', [
                {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
                {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
            ])
            with app.app_context():
                SurveyPoint.query.filter_by(file_id=fid).delete()
                db.session.commit()
                assert SurveyPoint.query.filter_by(file_id=fid).count() == 0
        finally:
            _drop_tenant(app, uid, tid)

    def test_point_code_field(self, app):
        from app.shared.models import SurveyPoint
        uid, tid = _make_tenant(app)
        try:
            fid = self._seed(app, tid, 'test_file', [
                {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0, 'code': 'BM1'},
                {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0, 'code': ''},
            ])
            with app.app_context():
                rows = SurveyPoint.query.filter_by(file_id=fid).order_by(SurveyPoint.point_no).all()
                assert rows[0].code == 'BM1'
                assert (rows[1].code or '') == ''
        finally:
            _drop_tenant(app, uid, tid)


class TestSettingsOperations:
    """Test settings operations."""

    def test_get_nonexistent_setting(self, app):
        from app.shared.models import Settings
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                assert Settings.get(tid, 'nonexistent', 'default_value') == 'default_value'
        finally:
            _drop_tenant(app, uid, tid)

    def test_set_and_get_setting(self, app):
        from app.shared.models import Settings
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                Settings.set(tid, 'company_name', 'test_value')
                assert Settings.get(tid, 'company_name') == 'test_value'
        finally:
            _drop_tenant(app, uid, tid)

    def test_settings_persistence(self, app):
        from app.shared.models import db, Settings
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                Settings.set(tid, 'phone', 'persist_value')
            db.session.remove()
            with app.app_context():
                assert Settings.get(tid, 'phone') == 'persist_value'
        finally:
            _drop_tenant(app, uid, tid)

    def test_get_all_settings(self, app):
        from app.shared.models import Settings
        uid, tid = _make_tenant(app)
        try:
            with app.app_context():
                Settings.set(tid, 'company_name', 'value1')
                Settings.set(tid, 'phone', 'value2')
                result = Settings.get_all(tid)
                assert result['company_name'] == 'value1'
                assert result['phone'] == 'value2'
        finally:
            _drop_tenant(app, uid, tid)
