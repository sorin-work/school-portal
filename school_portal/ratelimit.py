"""Counting failed sign-ins, per address and per client.

Attempts are rows in login_attempts, so the limit holds across workers and
restarts. Old rows are removed by the nightly housekeeping job.
"""

from datetime import timedelta

from flask import current_app
from sqlalchemy import delete, func, select

from . import timeutil
from .extensions import db
from .models import LoginAttempt

# A client is allowed more failures than one address, since a school's
# tablets and a family's phones can share one address.
PER_IP_FACTOR = 4


def _window_start():
    return timeutil.now() - timedelta(minutes=current_app.config["LOGIN_WINDOW_MINUTES"])


def _failures(column, value) -> int:
    since = _window_start()
    # A success clears the failures before it for that address.
    query = select(func.count()).where(
        column == value, LoginAttempt.success.is_(False), LoginAttempt.at >= since
    )
    if column is LoginAttempt.email:
        last_ok = db.session.scalar(
            select(func.max(LoginAttempt.at)).where(
                LoginAttempt.email == value, LoginAttempt.success.is_(True)
            )
        )
        if last_ok is not None:
            query = query.where(LoginAttempt.at > last_ok)
    return db.session.scalar(query) or 0


def login_blocked(email: str, ip: str) -> bool:
    limit = current_app.config["LOGIN_MAX_FAILURES"]
    if _failures(LoginAttempt.email, email) >= limit:
        return True
    return _failures(LoginAttempt.ip, ip) >= limit * PER_IP_FACTOR


def record(email: str, ip: str, *, success: bool) -> None:
    db.session.add(LoginAttempt(email=email[:254], ip=ip[:64], success=success))
    db.session.commit()


def prune(days: int = 7) -> int:
    cutoff = timeutil.now() - timedelta(days=days)
    result = db.session.execute(delete(LoginAttempt).where(LoginAttempt.at < cutoff))
    return result.rowcount or 0
