"""
File management routes for MAS - tenant-scoped.
"""
import os
from flask import (Blueprint, render_template, session, redirect, url_for,
                   request)

from app.shared.models import db, SurveyFile, SurveyPoint
from app.shared.middleware import (
    login_required, get_current_tenant,
    tenant_block_reason,
)

# __file__ = app/programs/mas/routes/files.py
MAS_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

files_bp = Blueprint('files', __name__, template_folder=MAS_TEMPLATES)


@files_bp.before_request
def _ensure_tenant():
    """Tenantless users (broken state) go to the waiting room."""
    if get_current_tenant() is None:
        return redirect(url_for('landing.waiting'))


@files_bp.route('/files')
@login_required
def list_files():
    """List all survey files for the current tenant."""
    files = SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id
    ).order_by(SurveyFile.created_at.desc()).all()
    return render_template('files.html', files=[f.to_dict() for f in files])


@files_bp.route('/files/new', methods=['GET', 'POST'])
@login_required
def new_file():
    """Create a new survey file (scoped to current tenant)."""
    if request.method == 'POST':
        data = request.form
        name = (data.get('name') or '').strip()
        date = data.get('date') or ''
        place = data.get('place') or ''

        if not name:
            return render_template('error.html', message='File name is required'), 400
        if len(name) > 200:
            return render_template('error.html', message='File name too long (max 200)'), 400

        tenant = get_current_tenant()
        reason = tenant_block_reason(tenant)
        if reason == 'suspended':
            return render_template(
                'error.html', message='Account suspended, contact platform owner'), 403
        if reason == 'pending':
            return render_template(
                'error.html', message='Subscription pending owner approval'), 403
        if reason in ('expired', 'no_tenant'):
            return render_template(
                'error.html', message='Subscription expired, please renew'), 403

        existing = SurveyFile.query.filter_by(
            tenant_id=tenant.id, name=name
        ).first()
        if existing:
            return render_template('error.html', message='File already exists'), 400

        f = SurveyFile(
            tenant_id=tenant.id,
            name=name, date=date, place=place,
        )
        db.session.add(f)
        db.session.commit()

        session['current_file'] = name
        return redirect(url_for('main.mas_menu'))

    return render_template('new_file.html')


@files_bp.route('/files/<name>')
@login_required
def view_file(name):
    """View a specific survey file (tenant-scoped)."""
    f = SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id, name=name
    ).first()
    if not f:
        return render_template('error.html', message='File not found'), 404

    session['current_file'] = name

    points = SurveyPoint.query.filter_by(
        tenant_id=get_current_tenant().id, file_id=f.id
    ).order_by(SurveyPoint.point_no).all()
    return render_template('view_file.html', file=f.to_dict(),
                           points=[p.to_dict() for p in points])


@files_bp.route('/files/<name>/delete', methods=['POST'])
@login_required
def delete_file(name):
    """Delete a survey file (tenant-scoped)."""
    f = SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id, name=name
    ).first()
    if not f:
        return render_template('error.html', message='File not found'), 404
    # Points cascade via SurveyFile.points relationship (delete-orphan).
    db.session.delete(f)
    db.session.commit()
    if session.get('current_file') == name:
        session.pop('current_file', None)
    return redirect(url_for('files.list_files'))
