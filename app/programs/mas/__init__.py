"""
MAS Program Module.
All routes, services and templates for MAS program.
"""
from flask import Blueprint

# Create MAS blueprint
mas_bp = Blueprint('mas', __name__,
                    template_folder='templates',
                    static_folder='static',
                    static_url_path='/mas/static')


def register_mas_routes(app):
    """Register all MAS routes with the app."""
    from .routes.main import main_bp
    from .routes.files import files_bp
    from .routes.api import api_bp
    
    app.register_blueprint(main_bp, url_prefix='/mas')
    app.register_blueprint(files_bp, url_prefix='/mas/files')
    app.register_blueprint(api_bp, url_prefix='/mas/api')
