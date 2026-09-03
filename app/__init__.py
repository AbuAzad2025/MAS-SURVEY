"""
MAS Web Application Factory.
PostgreSQL + SQLAlchemy + multi-tenant (every user = one tenant).
"""
from flask import Flask
from config import config


def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__,
                instance_relative_config=True,
                template_folder='templates',
                static_folder='static',
                static_url_path='/static')
    app.config.from_object(config[config_name])

    # Legacy alias for tests that read app.config['DATABASE'].
    app.config['DATABASE'] = app.config['SQLALCHEMY_DATABASE_URI']

    # SQLAlchemy
    from app.shared.models import db
    db.init_app(app)

    # Migrations
    from flask_migrate import Migrate
    from app.shared.models import db as _db
    Migrate(app, _db)

    with app.app_context():
        db.create_all()
        from app.shared.middleware import ensure_super_admin
        ensure_super_admin()

    # Shared, project-wide routes (landing/auth/admin) in the app root
    from app.routes.main import landing_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(landing_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)

    # Contained programs - each registered by name from app/programs/<name>
    from app.programs.mas import register_mas_routes
    register_mas_routes(app)

    return app
