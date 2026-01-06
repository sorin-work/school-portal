"""Role checks for views."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles: str):
    """Allow only users with one of these roles (administrators always pass)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles and not current_user.is_admin:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view):
    return roles_required("admin")(view)


def staff_required(view):
    return roles_required("staff")(view)
