"""
Main menu routes for MAS application.
"""
from flask import Blueprint, render_template, session, current_app
from app.shared.models import SurveyFile, SurveyPoint, Settings
import os

# Get the templates folder path for MAS program
# __file__ = app/programs/mas/routes/main.py
# Need: app/programs/mas/templates
MAS_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

main_bp = Blueprint('main', __name__, template_folder=MAS_TEMPLATES)


@main_bp.route('/')
def mas_menu():
    """
    MAS program main menu.
    """
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
def work_mode():
    """
    Work mode settings page.
    Allows configuration of angular units, printing options.
    """
    settings = get_settings()
    return render_template(
        'work_mode.html',
        settings=settings
    )


@main_bp.route('/polar')
def polar():
    """
    Polar survey page.
    For entering polar survey data (distomat, tacheometry, azimuth-distance).
    """
    file_info = get_current_file_info()
    if not file_info:
        return render_template('error.html', 
                            message='Please open or create a file first')
    
    return render_template('polar.html', file_info=file_info)


@main_bp.route('/offsets')
def offsets():
    """
    Offsets calculation page.
    """
    file_info = get_current_file_info()
    return render_template('offsets.html', file_info=file_info)


@main_bp.route('/circle')
def circle():
    """
    Circle calculations page.
    """
    return render_template('circle.html')


@main_bp.route('/intersections')
def intersections():
    """
    Intersections page.
    Two lines or distances intersection calculations.
    """
    return render_template('intersections.html')


@main_bp.route('/implants')
def implants():
    """
    Implantations page.
    Stake out points from known points and directions.
    """
    file_info = get_current_file_info()
    return render_template('implants.html', file_info=file_info)


@main_bp.route('/resection')
def resection():
    """
    Resection page.
    Calculate station position from known points and angles.
    """
    file_info = get_current_file_info()
    return render_template('resection.html', file_info=file_info)


@main_bp.route('/area')
def area():
    """
    Area calculation page.
    Calculates area from coordinate list.
    """
    file_info = get_current_file_info()
    points = get_current_points()
    return render_template('area.html', 
                         file_info=file_info,
                         points=points)


@main_bp.route('/plotting')
def plotting():
    """
    Plotting page.
    Grid limits and coordinate printing.
    """
    file_info = get_current_file_info()
    return render_template('plotting.html', file_info=file_info)


@main_bp.route('/plan')
def plan():
    """
    Plan on screen page.
    Simple coordinate display on screen.
    """
    file_info = get_current_file_info()
    points = get_current_points()
    return render_template('plan.html',
                         file_info=file_info,
                         points=points)


@main_bp.route('/print-preview')
def print_preview():
    """
    Print preview page.
    Shows formatted output for printing.
    """
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


@main_bp.route('/guide')
def user_guide():
    """
    User guide page.
    """
    import os
    
    # Path to USER_GUIDE.md - it's in the WEB_VERSION folder
    # __file__ = WEB_VERSION/app/programs/mas/routes/main.py
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    guide_path = os.path.join(base_dir, 'USER_GUIDE.md')
    
    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert markdown to HTML
        import re
        
        # Simple markdown to HTML conversion
        html = content
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'\|(.+)\|', lambda m: '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in m.group(1).split('|')) + '</tr>', html)
        html = re.sub(r'```[\s\S]*?```', lambda m: '<pre>' + m.group(0)[3:-3].strip() + '</pre>', html)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'\n\n+', r'</p><p>', html)
        html = '<p>' + html + '</p>'
        html = html.replace('</p><h', '</p><h')
        html = html.replace('</p><hr', '<hr')
        html = html.replace('<hr>', '</p><hr><p>')
        
        return render_template('guide.html', content=html)
    except Exception as e:
        return f"Error loading guide: {str(e)}", 500


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
