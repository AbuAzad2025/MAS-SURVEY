"""
Pytest fixtures for MAS Survey E2E tests.
Playwright drives a real Chromium against the Flask test server bound
to the mas_survey_test PostgreSQL DB (same as the rest of the suite).
"""
import os
import time
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get('E2E_BASE_URL', 'http://127.0.0.1:5099')
HEADLESS = os.environ.get('E2E_HEADLESS', 'true').lower() == 'true'
SLOW_MO = int(os.environ.get('E2E_SLOW_MO', '0'))


@pytest.fixture(scope='session')
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope='session')
def browser_config() -> dict:
    return {
        'headless': HEADLESS,
        'slow_mo': SLOW_MO,
        'args': ['--disable-web-security'],
    }


@pytest.fixture(scope='session')
def e2e_server(app):
    """Reuse the existing Flask test app, served on a real port via werkzeug.

    We DO NOT spawn a subprocess: that would point to a different DB
    (development env) and create race conditions with the test suite.
    """
    from werkzeug.serving import make_server
    from threading import Thread
    import re

    port = int(re.sub(r'.*:(\d+)$', r'\1', BASE_URL))
    server = make_server('127.0.0.1', port, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE_URL + '/', timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        server.shutdown()
        raise RuntimeError("E2E server did not come up")

    yield BASE_URL
    server.shutdown()


@pytest.fixture(scope='session')
def _browser(browser_config):
    with sync_playwright() as p:
        browser = p.chromium.launch(**browser_config)
        yield browser
        browser.close()


@pytest.fixture
def page(_browser, e2e_server):
    ctx = _browser.new_context(viewport={'width': 1366, 'height': 900})
    page = ctx.new_page()
    yield page
    ctx.close()


@pytest.fixture
def admin_page(page):
    """Page with admin already logged in."""
    page.goto(BASE_URL + '/auth/login')
    page.fill('#username', 'admin')
    page.fill('#password', 'admin123')
    page.click('button[type="submit"]')
    # Login is XHR; wait for the post-login navigation.
    page.wait_for_url(re.compile(r'.*/$'), timeout=5000)
    return page


import re  # used by admin_page
