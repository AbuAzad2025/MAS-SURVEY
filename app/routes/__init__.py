"""
Routes package for MAS application.
"""
from .main import main_bp
from .files import files_bp
from .api import api_bp

__all__ = ['main_bp', 'files_bp', 'api_bp']
