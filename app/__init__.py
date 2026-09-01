"""
MAS Web Application Factory.
Single source of truth for all routes and configuration.
"""
from flask import Flask
from config import config
import os


def create_app(config_name='default'):
    """
    Application factory pattern.
    All routes registered here - single source of truth.
    """
    app = Flask(__name__,
                instance_relative_config=True,
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
                static_url_path='/static')
    app.config.from_object(config[config_name])
    
    # Handle testing config - use temp file for testing
    if config_name == 'testing':
        import tempfile
        import atexit
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        app.config['DATABASE'] = db_path
        atexit.register(lambda: os.unlink(db_path) if os.path.exists(db_path) else None)
    
    db_path = app.config.get('DATABASE', '')
    if db_path and db_path != ':memory:':
        db_folder = os.path.dirname(db_path)
        if db_folder:
            os.makedirs(db_folder, exist_ok=True)
    
    from app.shared.models import init_db
    init_db(app.config['DATABASE'])
    
    from app.routes.auth import init_default_super_admin
    init_default_super_admin(app.config['DATABASE'])
    
    from app.routes.main import main_bp
    from app.routes.files import files_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp, url_prefix='/')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)
    
    return app
