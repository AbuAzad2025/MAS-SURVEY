"""
MAS main routes (contained in the MAS program).

All MAS page routes live here inside the isolated mas program package.
Shared landing/auth/admin routes remain in the app root.
"""
from flask import Blueprint, render_template, session, current_app, request, jsonify, redirect, url_for
from app.shared.models import SurveyFile, SurveyPoint, Settings
from app.routes.auth import login_required
import os

# __file__ = app/programs/mas/routes/main.py
MAS_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

main_bp = Blueprint('main', __name__, template_folder=MAS_TEMPLATES)


def get_settings():
    """Get application settings from session or database."""
    if 'settings' not in session:
        session['settings'] = Settings.get_all(current_app.config['DATABASE'])
    return session['settings']


def get_current_file_info():
    """Get current working file info."""
    file_name = session.get('current_file')
    if not file_name:
        return None
    return SurveyFile.get_by_name(current_app.config['DATABASE'], file_name)


def get_current_points():
    """Get points for current file."""
    file_name = session.get('current_file')
    if not file_name:
        return []
    return SurveyPoint.get_by_file(current_app.config['DATABASE'], file_name)


@main_bp.route('/mas')
@login_required
def mas_menu():
    """MAS program main menu."""
    settings = get_settings()
    files = SurveyFile.get_all(current_app.config['DATABASE'])
    file_info = get_current_file_info()
    return render_template(
        'mas_menu.html',
        settings=settings,
        files=files,
        file_info=file_info,
        company=settings.get('company_name', 'Alrafideen Surveying Office'),
        phone=settings.get('phone', '0562150193')
    )


@main_bp.route('/work-mode')
@login_required
def work_mode():
    """Work mode settings page."""
    settings = get_settings()
    return render_template('work_mode.html', settings=settings)


@main_bp.route('/polar')
@login_required
def polar():
    """Polar survey page (Distomat/Tacheometry/Azimuth-Distance)."""
    file_info = get_current_file_info()
    if not file_info:
        return render_template('error.html', message='Please open or create a file first')
    return render_template('polar.html', file_info=file_info)


@main_bp.route('/offsets')
@login_required
def offsets():
    """Offsets calculation page."""
    file_info = get_current_file_info()
    return render_template('offsets.html', file_info=file_info)


@main_bp.route('/circle')
@login_required
def circle():
    """Circle/Arc calculations page."""
    return render_template('circle.html')


@main_bp.route('/intersections')
@login_required
def intersections():
    """Intersections page (Two Lines/Distances)."""
    return render_template('intersections.html')


@main_bp.route('/implants')
@login_required
def implants():
    """Implantations page (Polar/Offsets stake out)."""
    file_info = get_current_file_info()
    return render_template('implants.html', file_info=file_info)


@main_bp.route('/resection')
@login_required
def resection():
    """Resection page (3-point resection with Tienstra)."""
    file_info = get_current_file_info()
    return render_template('resection.html', file_info=file_info)


@main_bp.route('/area')
@login_required
def area():
    """Area calculation page (Surveyor's formula)."""
    file_info = get_current_file_info()
    points = get_current_points()
    return render_template('area.html', file_info=file_info, points=points)


@main_bp.route('/traverse')
@login_required
def traverse():
    """Traverse adjustment page (Bowditch method)."""
    file_info = get_current_file_info()
    points = get_current_points()
    return render_template('traverse.html', file_info=file_info, points=points)


@main_bp.route('/plotting')
@login_required
def plotting():
    """Plotting page (Grid limits, Interpolation, Draw)."""
    file_info = get_current_file_info()
    return render_template('plotting.html', file_info=file_info)


@main_bp.route('/plan')
@login_required
def plan():
    """Plan on screen page."""
    file_info = get_current_file_info()
    points = get_current_points()
    return render_template('plan.html', file_info=file_info, points=points)


@main_bp.route('/print-preview')
@login_required
def print_preview():
    """Print preview page."""
    file_info = get_current_file_info()
    points = get_current_points()
    settings = get_settings()
    return render_template(
        'print_preview.html',
        file_info=file_info,
        points=points,
        settings=settings,
        company=settings.get('company_name', 'Alrafideen Surveying Office'),
        phone=settings.get('phone', '0562150193')
    )
