"""
Landing page routes.
"""
from flask import Blueprint, render_template

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """
    Landing page with all programs.
    """
    return render_template(
        'main_menu.html',
        company='Alrafideen Surveying Office',
        phone='0562150193'
    )
