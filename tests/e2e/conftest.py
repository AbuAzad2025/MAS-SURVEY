"""
Pytest configuration and fixtures for MAS Survey E2E tests.
"""
import os
import time
import pytest
from pathlib import Path
from playwright.sync_api import Browser, Page, sync_playwright


# Configuration
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
HEADLESS = os.environ.get('HEADLESS', 'true').lower() == 'true'
BROWSER = os.environ.get('BROWSER', 'chromium')
SLOW_MO = int(os.environ.get('SLOW_MO', '0'))


@pytest.fixture(scope='session')
def browser_config() -> dict:
    """Browser configuration for Playwright."""
    return {
        'headless': HEADLESS,
        'slow_mo': SLOW_MO,
        'args': [
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
    }


@pytest.fixture(scope='session')
def browser(browser_config: dict) -> Browser:
    """Launch browser for tests."""
    with sync_playwright() as p:
        if BROWSER == 'firefox':
            browser = p.firefox.launch(**browser_config)
        elif BROWSER == 'webkit':
            browser = p.webkit.launch(**browser_config)
        else:
            browser = p.chromium.launch(**browser_config)
        yield browser
        browser.close()


@pytest.fixture(scope='function')
def page(browser: Browser) -> Page:
    """Create new page for each test."""
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()


@pytest.fixture(scope='session')
def base_url() -> str:
    """Get base URL for tests."""
    return BASE_URL


@pytest.fixture(scope='session')
def app_server():
    """Start Flask development server for tests."""
    import subprocess
    import sys
    
    # Path to the Flask app
    app_path = Path(__file__).parent.parent / 'run.py'
    
    # Start server
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['TESTING'] = 'true'
    
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to start
    import urllib.request
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            urllib.request.urlopen(BASE_URL)
            break
        except Exception:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Server failed to start")
    
    yield process
    
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope='function')
def logged_in_session(page: Page, base_url: str):
    """Create a logged-in session."""
    page.goto(f"{base_url}/files/new")
    # If there's auth, handle it here
    yield page


@pytest.fixture(scope='function')
def create_test_file(page: Page, base_url: str) -> dict:
    """Create a test survey file with sample points."""
    file_name = f'test_{int(time.time())}'
    
    page.goto(f"{base_url}/files/new")
    page.fill('input[name="name"]', file_name)
    page.fill('input[name="date"]', '2026-08-31')
    page.fill('input[name="place"]', 'Test Location')
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/mas")
    
    # Add test points via API
    test_points = [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]
    
    page.evaluate(f"""
        fetch('/api/points', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{points: {test_points}}})
        }})
    """)
    
    return {'name': file_name, 'points': test_points}


@pytest.fixture(scope='function')
def login_as_test_user(page: Page, base_url: str):
    """Login as test user."""
    # If auth exists, implement here
    yield page


@pytest.fixture
def sample_dtf_file(tmp_path: Path) -> Path:
    """Create a sample DTF file for testing."""
    dtf_content = create_sample_dtf()
    file_path = tmp_path / 'sample.dtf'
    file_path.write_bytes(dtf_content)
    return file_path


def create_sample_dtf() -> bytes:
    """Create sample DTF file content."""
    import struct
    
    header = b'SAMPLE          '
    marker = b'\xDC\x05\x00\x00'
    date_str = b'31-8-2026     '
    
    points = [
        (1000.0, 2000.0, 50.0),
        (1100.0, 2000.0, 55.0),
        (1100.0, 2100.0, 60.0),
        (1000.0, 2100.0, 58.0),
    ]
    
    data = b''
    for y, x, h in points:
        data += struct.pack('<d', y)
        data += struct.pack('<d', x)
        data += struct.pack('<d', h)
    
    return header + marker + date_str + header + data


@pytest.fixture
def sample_points() -> list:
    """Sample survey points for testing."""
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]


@pytest.fixture
def sample_traverse_data() -> list:
    """Sample traverse data for testing."""
    return [
        {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'azimuth': 0.0, 'distance': 100.0},
        {'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0, 'azimuth': 100.0, 'distance': 100.0},
        {'no': 3, 'y': 100.0, 'x': 100.0, 'h': 0.0, 'azimuth': 200.0, 'distance': 100.0},
        {'no': 4, 'y': 0.0, 'x': 100.0, 'h': 0.0, 'azimuth': 300.0, 'distance': 100.0},
    ]
