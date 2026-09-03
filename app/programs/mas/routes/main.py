"""
MAS main routes - contained in the MAS program package.
PostgreSQL + SQLAlchemy + tenant-scoped.
"""
import os
from flask import Blueprint, render_template, session

from app.shared.models import SurveyFile, SurveyPoint, Settings
from app.shared.middleware import (
    login_required, get_current_tenant,
)

MAS_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

main_bp = Blueprint('main', __name__, template_folder=MAS_TEMPLATES)


# --- helpers -----------------------------------------------------------

def _get_settings() -> dict:
    """Tenant settings, cached in session."""
    if 'settings' not in session:
        session['settings'] = Settings.get_all(get_current_tenant().id)
    return session['settings']


def _get_current_file_info():
    """Return SurveyFile or None for the current working file."""
    name = session.get('current_file')
    if not name:
        return None
    return SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id, name=name
    ).first()


def _get_current_points() -> list:
    """Return list of SurveyPoint for the current working file."""
    f = _get_current_file_info()
    if not f:
        return []
    return SurveyPoint.query.filter_by(
        tenant_id=get_current_tenant().id, file_id=f.id
    ).order_by(SurveyPoint.point_no).all()


# --- routes ------------------------------------------------------------

@main_bp.route('/mas')
@login_required
def mas_menu():
    """MAS program main menu."""
    settings = _get_settings()
    files = SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id
    ).order_by(SurveyFile.created_at.desc()).all()
    file_info = _get_current_file_info()
    return render_template(
        'mas_menu.html',
        settings=settings, files=files, file_info=file_info,
        company=settings.get('company_name', 'Alrafideen Surveying Office'),
        phone=settings.get('phone', '0562150193'),
    )


@main_bp.route('/work-mode')
@login_required
def work_mode():
    return render_template('work_mode.html', settings=_get_settings())


@main_bp.route('/polar')
@login_required
def polar():
    f = _get_current_file_info()
    if not f:
        return render_template('error.html', message='Please open or create a file first')
    return render_template('polar.html', file_info=f.to_dict())


@main_bp.route('/offsets')
@login_required
def offsets():
    return render_template('offsets.html', file_info=_get_current_file_info().to_dict() if _get_current_file_info() else None)


@main_bp.route('/circle')
@login_required
def circle():
    return render_template('circle.html')


@main_bp.route('/intersections')
@login_required
def intersections():
    return render_template('intersections.html')


@main_bp.route('/implants')
@login_required
def implants():
    return render_template('implants.html', file_info=_get_current_file_info().to_dict() if _get_current_file_info() else None)


@main_bp.route('/resection')
@login_required
def resection():
    return render_template('resection.html', file_info=_get_current_file_info().to_dict() if _get_current_file_info() else None)


@main_bp.route('/area')
@login_required
def area():
    f = _get_current_file_info()
    points = _get_current_points()
    return render_template('area.html',
                           file_info=f.to_dict() if f else None,
                           points=[p.to_dict() for p in points])


@main_bp.route('/traverse')
@login_required
def traverse():
    f = _get_current_file_info()
    points = _get_current_points()
    return render_template('traverse.html',
                           file_info=f.to_dict() if f else None,
                           points=[p.to_dict() for p in points])


@main_bp.route('/plotting')
@login_required
def plotting():
    return render_template('plotting.html',
                           file_info=_get_current_file_info().to_dict() if _get_current_file_info() else None)


@main_bp.route('/plan')
@login_required
def plan():
    f = _get_current_file_info()
    points = _get_current_points()
    return render_template('plan.html',
                           file_info=f.to_dict() if f else None,
                           points=[p.to_dict() for p in points])


@main_bp.route('/print-preview')
@login_required
def print_preview():
    f = _get_current_file_info()
    points = _get_current_points()
    settings = _get_settings()
    return render_template(
        'print_preview.html',
        file_info=f.to_dict() if f else None,
        points=[p.to_dict() for p in points],
        settings=settings,
        company=settings.get('company_name', 'Alrafideen Surveying Office'),
        phone=settings.get('phone', '0562150193'),
    )
