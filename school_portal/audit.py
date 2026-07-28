"""Recording who viewed or changed a child's record."""

from datetime import timedelta

from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import select

from . import timeutil
from .extensions import db
from .models import AuditEntry

# Views by the same person within this window are recorded once.
VIEW_WINDOW = timedelta(minutes=30)


def record(action: str, child=None, target: str | None = None, **details) -> None:
    actor_id = None
    ip = None
    if has_request_context():
        ip = request.remote_addr
        if current_user.is_authenticated:
            actor_id = current_user.id
    child_id = child if isinstance(child, int) or child is None else child.id
    db.session.add(
        AuditEntry(
            actor_id=actor_id,
            action=action,
            child_id=child_id,
            target=target,
            details=details,
            ip=ip,
        )
    )


def record_view(child, what: str = "profile") -> None:
    """Record that the current user opened a child's record, at most once per window."""
    if not current_user.is_authenticated:
        return
    since = timeutil.now() - VIEW_WINDOW
    recent = db.session.scalar(
        select(AuditEntry.id).where(
            AuditEntry.actor_id == current_user.id,
            AuditEntry.child_id == child.id,
            AuditEntry.action == "child.viewed",
            AuditEntry.target == what,
            AuditEntry.at >= since,
        )
    )
    if recent is None:
        record("child.viewed", child, target=what)
        db.session.commit()
