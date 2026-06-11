from functools import wraps

from flask import abort
from flask_login import current_user


def roles_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_role(*roles):
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


admin_required = roles_required('admin')
manager_required = roles_required('admin', 'manager')
