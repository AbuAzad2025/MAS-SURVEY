"""
Landing Page Module.
"""
from flask import Blueprint

landing_bp = Blueprint('landing', __name__,
                       template_folder='templates')

def register_landing_routes(app):
    """Register landing routes."""
    from .routes import landing_bp
    app.register_blueprint(landing_bp)
