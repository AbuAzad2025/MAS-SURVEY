"""
MAS Program Module.
All routes, services and templates for MAS program are contained here.

This program is registered with the SAME URLs the app previously exposed
(no /mas/ prefix) so existing links, bookmarks and tests keep working:
  - main_bp  ->  /mas, /polar, /area, ... (root-level)
  - files_bp ->  /files...
  - api_bp   ->  /api...
"""


def register_mas_routes(app):
    """Register all MAS routes with the app, preserving existing URLs."""
    from .routes.main import main_bp
    from .routes.files import files_bp
    from .routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp, url_prefix='/')
    app.register_blueprint(api_bp, url_prefix='/api')
