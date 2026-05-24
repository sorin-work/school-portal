"""In-app notifications."""

from collections.abc import Iterable

from .extensions import db
from .models import Notification, User


def notify(users: Iterable[User], kind: str, title: str, url: str | None = None, child=None) -> int:
    """Add a notification for each user (once each), in the current transaction."""
    seen: set[int] = set()
    for user in users:
        if user.id in seen or not user.active:
            continue
        seen.add(user.id)
        db.session.add(
            Notification(
                user_id=user.id,
                kind=kind,
                title=title[:200],
                url=url,
                child_id=child.id if child is not None else None,
            )
        )
    return len(seen)
