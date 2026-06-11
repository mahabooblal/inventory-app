"""API utilities: JWT and authentication decorators."""

import jwt
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app, g, request
from app.api.base import (
    APIResponse,
    ValidationError,
    require_json,
    parse_pagination_params,
    parse_filter_params,
    parse_sort_params,
    parse_search_params,
)


class JWTManager:
    """JWT token management for API authentication."""
    
    def __init__(self, secret_key=None, access_token_expires=3600, refresh_token_expires=2592000):
        self.secret_key = secret_key or os.environ.get(
            'JWT_SECRET_KEY',
            'dev-secret-key-0123456789abcdef'
        )
        self.access_token_expires = access_token_expires  # 1 hour
        self.refresh_token_expires = refresh_token_expires  # 30 days
        self.blacklist = set()  # Token revocation in-memory (use Redis for production)
    
    def generate_tokens(self, user_id, username, role):
        """Generate access and refresh tokens."""
        now = datetime.now(timezone.utc)
        
        access_payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(seconds=self.access_token_expires),
            'jti': secrets.token_urlsafe(16),
        }
        
        refresh_payload = {
            'user_id': user_id,
            'username': username,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(seconds=self.refresh_token_expires),
            'jti': secrets.token_urlsafe(16),
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')
        
        # Ensure string return for PyJWT compatibility
        if isinstance(access_token, bytes):
            access_token = access_token.decode('utf-8')
        if isinstance(refresh_token, bytes):
            refresh_token = refresh_token.decode('utf-8')
        
        return access_token, refresh_token
    
    def verify_token(self, token, token_type='access'):
        """Verify and decode a token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            if payload.get('type') != token_type:
                return None
            if token in self.blacklist:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token):
        """Revoke a token (add to blacklist)."""
        self.blacklist.add(token)
    
    def is_token_revoked(self, token):
        """Check if token is revoked."""
        return token in self.blacklist


def get_jwt_manager():
    """Get or create JWT manager instance."""
    if not hasattr(g, 'jwt_manager'):
        g.jwt_manager = JWTManager(current_app.config.get('JWT_SECRET_KEY'))
    return g.jwt_manager


def token_required(token_type='access'):
    """Decorator to require valid JWT token."""
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            token = None
            
            # Extract token from Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(' ')[1]
                except IndexError:
                    return APIResponse.error('Invalid authorization header', status_code=401, error_code='INVALID_HEADER')
            
            if not token:
                return APIResponse.error('Token is missing', status_code=401, error_code='TOKEN_MISSING')
            
            jwt_manager = get_jwt_manager()
            payload = jwt_manager.verify_token(token, token_type=token_type)
            
            if not payload:
                return APIResponse.error('Invalid or expired token', status_code=401, error_code='INVALID_TOKEN')
            
            # Store token info in g for access in route
            g.jwt_payload = payload
            g.token = token
            
            return func(*args, **kwargs)
        
        return decorated_function
    return decorator


def role_required(*roles):
    """Decorator to require specific roles (requires token_required first)."""
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            payload = getattr(g, 'jwt_payload', None)
            if not payload:
                return APIResponse.error('Token not provided or invalid', status_code=401, error_code='TOKEN_MISSING')
            
            if payload.get('role') not in roles:
                return APIResponse.error('Insufficient permissions', status_code=403, error_code='FORBIDDEN')
            
            return func(*args, **kwargs)
        
        return decorated_function
    return decorator


def get_pagination_params():
    return parse_pagination_params()


def get_filter_and_sort_params():
    return parse_filter_params(), *parse_sort_params()
