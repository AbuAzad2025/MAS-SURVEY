"""
Activity viewer routes (super admin only).
"""
from flask import Blueprint, request, jsonify, render_template

from app.shared.middleware import super_admin_required
from app.shared.models import db, User
from app.shared.models.billing import ActivityLog


activity_bp = Blueprint('activity', __name__, url_prefix='/admin')


@activity_bp.route('/activity')
@super_admin_required
def activity_page():
    """Activity log page."""
    return render_template('admin/activity.html')


@activity_bp.route('/api/activity')
@super_admin_required
def api_activity():
    """Activity log API with optional action filter."""
    try:
        limit = int(request.args.get('limit', 100))
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(500, limit))

    action = (request.args.get('action') or '').strip()

    q = ActivityLog.query
    if action:
        q = q.filter_by(action=action)
    rows = q.order_by(ActivityLog.created_at.desc()).limit(limit).all()

    logs = []
    for r in rows:
        username = None
        if r.user_id:
            u = db.session.get(User, r.user_id)
            username = u.username if u else None
        logs.append({
            'id': r.id,
            'username': username,
            'action': r.action,
            'entity_type': r.entity_type,
            'entity_id': r.entity_id,
            'details': r.details,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        })
    return jsonify({'logs': logs})
