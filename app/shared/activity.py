"""
Activity logging helper.

Silent audit writer for user/tenant actions. Never raises.
"""
import json


def log_action(action, entity_type=None, entity_id=None, details=None, tenant_id=None):
    """Insert one ActivityLog row. Never raises.

    Reads ``user_id``/``tenant_id`` from the Flask session; the explicit
    ``tenant_id`` param overrides the session value.
    """
    try:
        from flask import session
        from app.shared.models import db
        from app.shared.models.billing import ActivityLog

        user_id = session.get('user_id')
        if tenant_id is None:
            tenant_id = session.get('tenant_id')

        if isinstance(details, (dict, list)):
            try:
                details = json.dumps(details, ensure_ascii=False)
            except Exception:
                details = str(details)

        entry = ActivityLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        try:
            from app.shared.models import db as _db
            _db.session.rollback()
        except Exception:
            pass
        pass
