"""
MAS Routes Package.

Exposes all blueprints for the MAS program. Imports are lazy so that
registering MAS does not eagerly import heavy modules.
"""


def get_main_bp():
    from .main import main_bp
    return main_bp


def get_files_bp():
    from .files import files_bp
    return files_bp


def get_api_bp():
    from .api import api_bp
    return api_bp
