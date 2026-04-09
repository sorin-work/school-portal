"""A child's diary, one day at a time."""

from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import access, photos, timeutil
from ..events import day_events
from ..extensions import db
from ..models import Event

bp = Blueprint("timeline", __name__)


def visible_events(child, day):
    events = day_events([child.id], day)
    if current_user.is_staff:
        return events
    return [e for e in events if e.visibility == "parents"]


def photos_for(event: Event) -> list:
    """The photos of an event this user may see."""
    items = [p.media for p in event.photos]
    if current_user.is_staff or not items:
        return items
    shown = []
    for media in items:
        tagged = photos.children_in(media.id)
        if photos.visible_to_family_of(event.child, tagged):
            shown.append(media)
    return shown


@bp.get("/children/<int:child_id>/diary")
@login_required
def child_day(child_id: int):
    child = access.child_or_404(child_id)
    day = timeutil.parse_day(request.args.get("day"))
    if day > timeutil.today():
        day = timeutil.today()
    events = visible_events(child, day)
    context = {}
    return render_template(
        "timeline/day.html",
        child=child,
        day=day,
        events=events,
        previous=day - timedelta(days=1),
        following=day + timedelta(days=1) if day < timeutil.today() else None,
        photos_for=photos_for,
        **context,
    )


@bp.post("/events/<int:event_id>/acknowledge")
@login_required
def acknowledge(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None or event.deleted_at is not None or not event.needs_ack:
        abort(404)
    child = access.child_or_404(event.child_id)
    if event.acknowledged_at is None:
        event.acknowledged_at = timeutil.now()
        event.acknowledged_by_id = current_user.id
        db.session.commit()
        flash("Thank you, the staff can see that you have read it.", "success")
    return redirect(
        url_for("timeline.child_day", child_id=child.id, day=timeutil.fmt_isoday(event.occurred_at))
        + f"#event-{event.id}"
    )
