"""
Pytest fixtures for CLI tests - autouse login for protected endpoints.
"""
import pytest


@pytest.fixture(autouse=True)
def login_for_protected_endpoints(client, super_admin_user):
    client.post('/auth/login', json={
        'username': super_admin_user['username'],
        'password': 'admin123',
    })
    return client
