"""
Shared root routes package.

Contains only project-wide, shared routes (landing, auth, admin).
Program-specific routes live inside each program folder under
app/programs/<name>/routes/.
"""
from .main import landing_bp
from .auth import auth_bp
from .admin import admin_bp

__all__ = ['landing_bp', 'auth_bp', 'admin_bp']
