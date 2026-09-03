"""
Shared root routes - Landing page and user guide.

These are common, project-wide routes that live in the app root and are
shared by all contained programs (MAS, INHERITANCE, ...).
"""
from flask import Blueprint, render_template
import os

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """Landing page: list of all programs."""
    return render_template('main_menu.html',
                           company='Alrafideen Surveying Office',
                           phone='0562150193')


@landing_bp.route('/guide')
def user_guide():
    """User guide page."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    guide_path = os.path.join(base_dir, 'USER_GUIDE.md')

    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        html = content
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'\|(.+)\|', lambda m: '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in m.group(1).split('|')) + '</tr>', html)
        html = re.sub(r'```[\s\S]*?```', lambda m: '<pre>' + m.group(0)[3:-3].strip() + '</pre>', html)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'\n\n+', r'</p><p>', html)
        html = '<p>' + html + '</p>'
        html = html.replace('</p><h', '</p><h')
        html = html.replace('</p><hr', '<hr')
        html = html.replace('<hr>', '</p><hr><p>')

        return render_template('guide.html', content=html)
    except Exception as e:
        return f"Error loading guide: {str(e)}", 500
