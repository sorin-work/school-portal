"""Deleting the records of children who have left, after the retention period.

When an administrator marks a child as left, purge_after is set to the last
day plus the "retention_days" setting. The nightly housekeeping job deletes
every child whose date has passed, unless the record is on hold (for example
while a complaint or a claim is open).
"""

from datetime import date

from sqlalchemy import func, select, update

from . import audit, timeutil, uploads
from .extensions import db
from .models import AuditEntry, Child, Collector, Event, EventMedia, Media


def due(today: date | None = None) -> list[Child]:
    today = today or timeutil.today()
    return list(
        db.session.scalars(
            select(Child).where(
                Child.purge_after.is_not(None),
                Child.purge_after <= today,
                Child.retention_hold.is_(False),
            )
        )
    )


def purge_child(child: Child, *, reason: str = "retention") -> dict:
    """Delete a child and everything about them. Returns counts for the log."""
    event_ids = select(Event.id).where(Event.child_id == child.id)
    media_ids = set(
        db.session.scalars(select(EventMedia.media_id).where(EventMedia.event_id.in_(event_ids)))
    )
    # A group photo stays while another child's event still uses it.
    shared = set(
        db.session.scalars(
            select(EventMedia.media_id)
            .join(Event, Event.id == EventMedia.event_id)
            .where(EventMedia.media_id.in_(media_ids), Event.child_id != child.id)
        )
    )
    collector_photos = set(
        db.session.scalars(
            select(Collector.photo_id).where(
                Collector.child_id == child.id, Collector.photo_id.is_not(None)
            )
        )
    )
    doomed = (media_ids - shared) | collector_photos
    counts = {
        "events": db.session.scalar(select(func.count()).select_from(event_ids.subquery())) or 0,
        "photos_deleted": len(doomed),
        "photos_kept_for_others": len(shared),
    }
    child_id = child.id
    db.session.delete(child)
    db.session.flush()
    for media in db.session.scalars(select(Media).where(Media.id.in_(doomed))):
        uploads.delete_files(media)
        db.session.delete(media)
    # Earlier entries keep their time and action, but lose names and details.
    db.session.execute(
        update(AuditEntry).where(AuditEntry.child_id == child_id).values(target=None, details={})
    )
    audit.record("child.purged", child_id, reason=reason, **counts)
    return counts


def purge_due(today: date | None = None) -> int:
    children = due(today)
    for child in children:
        purge_child(child)
    db.session.commit()
    return len(children)
