from functools import wraps
from flask import request, g
from app.api.response import json_error
from app.api.utils import get_jwt_manager


def token_required(token_type='access'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            parts = auth_header.split(' ')
            if len(parts) != 2 or parts[0] != 'Bearer':
                return json_error('Invalid authorization header', error_code='INVALID_HEADER', status_code=401)

            token = parts[1]
            jwt_manager = get_jwt_manager()
            payload = jwt_manager.verify_token(token, token_type=token_type)
            if not payload:
                return json_error('Invalid or expired token', error_code='INVALID_TOKEN', status_code=401)

            g.jwt_payload = payload
            g.token = token
            return func(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            payload = getattr(g, 'jwt_payload', None)
            if not payload:
                return json_error('Token not provided or invalid', error_code='TOKEN_MISSING', status_code=401)
            if payload.get('role') not in roles:
                return json_error('Insufficient permissions', error_code='FORBIDDEN', status_code=403)
            return func(*args, **kwargs)
        return wrapper
    return decorator
