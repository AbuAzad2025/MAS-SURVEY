"""
File management routes for MAS application.
"""
from flask import Blueprint, render_template, session, current_app, redirect, url_for

files_bp = Blueprint('files', __name__)


@files_bp.route('/files')
def list_files():
    """List all survey files."""
    from app.shared.models import SurveyFile
    
    files = SurveyFile.get_all(current_app.config['DATABASE'])
    return render_template('files.html', files=files)


@files_bp.route('/files/new', methods=['GET', 'POST'])
def new_file():
    """Create a new survey file."""
    from flask import request
    from app.shared.models import SurveyFile
    
    if request.method == 'POST':
        data = request.form
        name = data.get('name', '').strip()
        date = data.get('date', '')
        place = data.get('place', '')
        
        if not name:
            return render_template('error.html', message='File name is required')
        
        result = SurveyFile.create(
            current_app.config['DATABASE'],
            name=name,
            date=date,
            place=place
        )
        
        if not result:
            return render_template('error.html', message='File already exists')
        
        session['current_file'] = name
        return redirect(url_for('main.mas_menu'))
    
    return render_template('new_file.html')


@files_bp.route('/files/<name>')
def view_file(name):
    """View a specific survey file."""
    from app.shared.models import SurveyFile, SurveyPoint
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], name)
    if not file_info:
        return render_template('error.html', message='File not found')
    
    session['current_file'] = name
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], name)
    
    return render_template('view_file.html', 
                         file=file_info,
                         points=points)


@files_bp.route('/files/<name>/delete', methods=['POST'])
def delete_file(name):
    """Delete a survey file."""
    from app.shared.models import SurveyFile
    from flask import redirect, url_for
    
    SurveyFile.delete(current_app.config['DATABASE'], name)
    
    if session.get('current_file') == name:
        session.pop('current_file', None)
    
    return redirect(url_for('files.list_files'))
