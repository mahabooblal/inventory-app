"""Tests for API authentication endpoints."""

import json
import pytest
from datetime import datetime, timedelta
from app.models import User
from app.api.utils import JWTManager


@pytest.fixture
def api_client(app, database):
    """Create a test client for API endpoints with a database."""
    return app.test_client()


@pytest.fixture
def auth_user(admin_user):
    """Reuse admin user for auth tests."""
    return admin_user


def test_api_login_success(api_client, admin_user):
    """Test successful login returns access and refresh tokens."""
    response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'data' in data
    assert 'access_token' in data['data']
    assert 'refresh_token' in data['data']
    assert data['data']['user']['username'] == 'admin'
    assert data['data']['user']['role'] == 'admin'


def test_api_login_invalid_credentials(api_client):
    """Test login with invalid credentials."""
    response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'wrong_password'},
        content_type='application/json'
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['error_code'] == 'INVALID_CREDENTIALS'


def test_api_login_missing_fields(api_client):
    """Test login with missing username or password."""
    response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin'},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['error_code'] == 'MISSING_FIELDS'


def test_api_get_current_user(api_client, admin_user):
    """Test getting current user info with valid token."""
    # First login to get token
    login_response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    access_token = json.loads(login_response.data)['data']['access_token']
    
    # Get current user
    response = api_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['username'] == 'admin'
    assert data['data']['email'] == 'admin@example.com'
    assert data['data']['role'] == 'admin'


def test_api_get_current_user_no_token(api_client):
    """Test getting current user without token."""
    response = api_client.get('/api/v1/auth/me')
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['error_code'] == 'TOKEN_MISSING'


def test_api_get_current_user_invalid_token(api_client):
    """Test getting current user with invalid token."""
    response = api_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': 'Bearer invalid_token'}
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['error_code'] == 'INVALID_TOKEN'


def test_api_refresh_token(api_client, auth_user):
    """Test refreshing access token with refresh token."""
    # Login to get tokens
    login_response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    refresh_token = json.loads(login_response.data)['data']['refresh_token']
    
    # Refresh token
    response = api_client.post(
        '/api/v1/auth/refresh',
        headers={'Authorization': f'Bearer {refresh_token}'}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'access_token' in data['data']
    assert data['data']['access_token'] != json.loads(login_response.data)['data']['access_token']


def test_api_refresh_token_invalid(api_client):
    """Test refreshing token with invalid refresh token."""
    response = api_client.post(
        '/api/v1/auth/refresh',
        headers={'Authorization': 'Bearer invalid_token'}
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'


def test_api_logout(api_client, auth_user):
    """Test logout revokes access token."""
    # Login to get token
    login_response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    access_token = json.loads(login_response.data)['data']['access_token']
    
    # Logout
    logout_response = api_client.post(
        '/api/v1/auth/logout',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    assert logout_response.status_code == 200
    
    # Try to use revoked token - should fail
    me_response = api_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    assert me_response.status_code == 401


def test_jwt_manager_generate_tokens():
    """Test JWT token generation."""
    manager = JWTManager(secret_key='test-secret-key-0123456789abcdef1234')
    access_token, refresh_token = manager.generate_tokens(1, 'testuser', 'admin')
    
    assert access_token
    assert refresh_token
    assert access_token != refresh_token


def test_jwt_manager_verify_token():
    """Test JWT token verification."""
    manager = JWTManager(secret_key='test-secret-key-0123456789abcdef1234')
    access_token, _ = manager.generate_tokens(1, 'testuser', 'admin')
    
    payload = manager.verify_token(access_token, token_type='access')
    assert payload is not None
    assert payload['user_id'] == 1
    assert payload['username'] == 'testuser'
    assert payload['role'] == 'admin'
    assert payload['type'] == 'access'


def test_jwt_manager_verify_invalid_token():
    """Test JWT verification with invalid token."""
    manager = JWTManager(secret_key='test-secret')
    
    payload = manager.verify_token('invalid_token', token_type='access')
    assert payload is None


def test_jwt_manager_revoke_token():
    """Test JWT token revocation."""
    manager = JWTManager(secret_key='test-secret-key-0123456789abcdef1234')
    access_token, _ = manager.generate_tokens(1, 'testuser', 'admin')
    
    # Token should be valid before revocation
    payload = manager.verify_token(access_token, token_type='access')
    assert payload is not None
    
    # Revoke token
    manager.revoke_token(access_token)
    
    # Token should be invalid after revocation
    payload = manager.verify_token(access_token, token_type='access')
    assert payload is None


def test_api_authorization_header_parsing(api_client):
    """Test authorization header parsing."""
    # Test missing Bearer prefix
    response = api_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': 'invalid_token'}
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['error_code'] == 'INVALID_HEADER'


def test_api_login_creates_audit_log(api_client, auth_user, database):
    """Test that login creates an audit log entry."""
    from app.models import AuditLog
    
    # Clear existing logs
    AuditLog.query.delete()
    
    response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    # Check audit log
    audit = AuditLog.query.filter_by(action='LOGIN').first()
    assert audit is not None
    assert audit.result == 'success'


def test_api_logout_creates_audit_log(api_client, auth_user, database):
    """Test that logout creates an audit log entry."""
    from app.models import AuditLog
    
    # Clear existing logs
    AuditLog.query.delete()
    
    # Login
    login_response = api_client.post(
        '/api/v1/auth/login',
        json={'username': 'admin', 'password': 'password'},
        content_type='application/json'
    )
    access_token = json.loads(login_response.data)['data']['access_token']
    
    # Clear logs from login
    AuditLog.query.delete()
    
    # Logout
    logout_response = api_client.post(
        '/api/v1/auth/logout',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    assert logout_response.status_code == 200
    
    # Check audit log
    audit = AuditLog.query.filter_by(action='LOGOUT').first()
    assert audit is not None
    assert audit.result == 'success'
