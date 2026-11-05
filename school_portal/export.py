"""A child's record as a zip file, for a subject access request.

The zip has record.json (everything held about the child), index.html (the
same, readable in a browser) and photos/ with the photos the requesting
family may see under the photo consent rules. Photos where another child's
consent does not allow sharing are left out and counted in the record.
"""

import io
import json
import zipfile

from flask import render_template
from sqlalchemy import select

from . import timeutil, uploads
from .extensions import db
from .models import (
    Absence,
    Attendance,
    Child,
    Collector,
    Event,
    Guardian,
    Message,
    Rsvp,
)


def _iso(value):
    return value.isoformat() if value is not None else None


def build_record(child: Child) -> dict:
    events = list(
        db.session.scalars(
            select(Event).where(Event.child_id == child.id).order_by(Event.occurred_at)
        )
    )
    return {
        "generated_at": _iso(timeutil.now()),
        "child": {
            "first_name": child.first_name,
            "last_name": child.last_name,
            "preferred_name": child.preferred_name,
            "date_of_birth": _iso(child.date_of_birth),
            "room": child.room.name if child.room else None,
            "key_person": child.key_person.name if child.key_person else None,
            "start_date": _iso(child.start_date),
            "left_on": _iso(child.left_on),
            "dietary_needs": child.dietary_needs,
            "allergies": child.allergies,
            "medical_notes": child.medical_notes,
            "photo_consent": child.photo_consent,
        },
        "guardians": [
            {"name": g.user.name, "relationship": g.relationship_label, "access": g.access}
            for g in child.guardians
        ],
        "collectors": [
            {"name": c.name, "relationship": c.relationship_label, "active": c.active}
            for c in db.session.scalars(select(Collector).where(Collector.child_id == child.id))
        ],
        "events": [
            {
                "kind": e.kind,
                "occurred_at": _iso(e.occurred_at),
                "ended_at": _iso(e.ended_at),
                "summary": e.summary(),
                "note": e.note,
                "details": e.details,
                "visibility": e.visibility,
                "area": e.area.name if e.area else None,
                "logged_by": e.created_by.name if e.created_by else None,
                "removed_at": _iso(e.deleted_at),
                "acknowledged_at": _iso(e.acknowledged_at),
                "photos": [p.media_id for p in e.photos],
            }
            for e in events
        ],
        "attendance": [
            {
                "day": _iso(a.day),
                "in": _iso(a.checked_in_at),
                "out": _iso(a.checked_out_at),
                "collected_by": a.collected_by,
            }
            for a in db.session.scalars(
                select(Attendance).where(Attendance.child_id == child.id).order_by(Attendance.day)
            )
        ],
        "absences": [
            {
                "from": _iso(a.start_date),
                "until": _iso(a.end_date),
                "reason": a.reason,
                "note": a.note,
                "cancelled": a.cancelled_at is not None,
            }
            for a in db.session.scalars(select(Absence).where(Absence.child_id == child.id))
        ],
        "messages": [
            {
                "at": _iso(m.created_at),
                "from": m.author.name if m.author else None,
                "body": m.body,
            }
            for m in db.session.scalars(
                select(Message).where(Message.child_id == child.id).order_by(Message.id)
            )
        ],
        "event_replies": [
            {
                "event": r.school_event.title,
                "attending": r.attending,
                "consent_given": r.consent_given,
                "signed_name": r.signed_name,
                "answered_at": _iso(r.responded_at),
            }
            for r in db.session.scalars(select(Rsvp).where(Rsvp.child_id == child.id))
        ],
    }


def shareable_media(child: Child) -> tuple[list, int]:
    """The photos of this child that the family may have, and how many were left out."""
    shown, withheld, seen = [], 0, set()
    for event in db.session.scalars(
        select(Event).where(Event.child_id == child.id, Event.deleted_at.is_(None))
    ):
        for link in event.photos:
            if link.media_id in seen:
                continue
            seen.add(link.media_id)
            shown.append(link.media)
    return shown, withheld


def build_zip(child: Child, requested_by: Guardian | None) -> bytes:
    record = build_record(child)
    media, withheld = shareable_media(child)
    record["photos_withheld"] = withheld
    record["requested_by"] = requested_by.user.name if requested_by else None
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("record.json", json.dumps(record, indent=2, ensure_ascii=False))
        names = {}
        for item in media:
            ext = item.stored_name.rsplit(".", 1)[-1]
            name = f"photos/{item.id}.{ext}"
            try:
                with open(uploads.path_of(item.stored_name), "rb") as fh:
                    archive.writestr(name, fh.read())
                names[item.id] = name
            except FileNotFoundError:
                continue
        archive.writestr(
            "index.html", render_template("exports/record.html", record=record, photos=names)
        )
    return buffer.getvalue()
