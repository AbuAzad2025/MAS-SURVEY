"""
Main pytest configuration for MAS Survey tests.
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end browser tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "cli: CLI tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time")


@pytest.fixture(scope='session')
def project_root_path():
    """Get project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope='session')
def test_data_dir(project_root_path):
    """Get test data directory."""
    return project_root_path / 'tests' / 'fixtures'


@pytest.fixture(scope='session')
def base_url():
    """Get base URL for tests."""
    return os.environ.get('TEST_BASE_URL', 'http://localhost:5000')


@pytest.fixture(autouse=True)
def reset_app_state(app):
    """Reset application state between tests."""
    yield
    # Cleanup after test
    pass


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing."""
    from app import create_app
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope='session')
def sample_points():
    """Sample survey points for testing."""
    return [
        {'no': 1, 'y': 1000.0, 'x': 2000.0, 'h': 50.0},
        {'no': 2, 'y': 1100.0, 'x': 2000.0, 'h': 55.0},
        {'no': 3, 'y': 1100.0, 'x': 2100.0, 'h': 60.0},
        {'no': 4, 'y': 1000.0, 'x': 2100.0, 'h': 58.0},
    ]
