"""JWT Authentication API endpoints."""

from flask import Blueprint, request, g
from app import db
from app.models import User
from app.models.audit_log import log_audit_event
from app.api.utils import APIResponse, JWTManager, token_required, get_jwt_manager, require_json

bp = Blueprint('api_auth', __name__, url_prefix='/api/v1/auth')


@bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint to obtain JWT access and refresh tokens.
    
    Request body:
    {
        "username": "admin",
        "password": "password123"
    }
    """
    data = require_json()

    if not data.get('username') or not data.get('password'):
        return APIResponse.error('Username and password are required', status_code=400, error_code='MISSING_FIELDS')
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        log_audit_event(None, request, 'LOGIN_FAILED', data['username'], 'invalid_credentials')
        return APIResponse.error('Invalid username or password', status_code=401, error_code='INVALID_CREDENTIALS')
    
    jwt_manager = get_jwt_manager()
    access_token, refresh_token = jwt_manager.generate_tokens(user.id, user.username, user.role)
    
    log_audit_event(user, request, 'LOGIN', user.username, 'success')
    
    return APIResponse.success(
        data={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
        },
        message='Login successful',
        status_code=200
    )


@bp.route('/refresh', methods=['POST'])
@token_required(token_type='refresh')
def refresh():
    """
    Refresh access token using a refresh token.
    
    Header:
    Authorization: Bearer <refresh_token>
    """
    payload = g.jwt_payload
    
    user_id = payload.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return APIResponse.error('User not found', status_code=401, error_code='USER_NOT_FOUND')
    
    jwt_manager = get_jwt_manager()
    access_token, _ = jwt_manager.generate_tokens(user.id, user.username, user.role)
    
    return APIResponse.success(
        data={'access_token': access_token},
        message='Token refreshed',
        status_code=200
    )


@bp.route('/logout', methods=['POST'])
@token_required(token_type='access')
def logout():
    """
    Logout by revoking the access token.
    
    Header:
    Authorization: Bearer <access_token>
    """
    token = g.token
    jwt_manager = get_jwt_manager()
    jwt_manager.revoke_token(token)
    
    payload = g.jwt_payload
    user = db.session.get(User, payload.get('user_id'))
    
    if user:
        log_audit_event(user, request, 'LOGOUT', user.username, 'success')
    
    return APIResponse.success(
        data=None,
        message='Logout successful',
        status_code=200
    )


@bp.route('/me', methods=['GET'])
@token_required(token_type='access')
def get_current_user():
    """
    Get the current authenticated user info.
    
    Header:
    Authorization: Bearer <access_token>
    """
    payload = g.jwt_payload
    user = db.session.get(User, payload.get('user_id'))
    
    if not user:
        return APIResponse.error('User not found', status_code=404, error_code='USER_NOT_FOUND')
    
    return APIResponse.success(
        data={
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        },
        message='User info retrieved',
        status_code=200
    )
