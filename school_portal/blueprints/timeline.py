"""A child's diary, one day at a time."""

from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from .. import access, photos, timeutil
from ..events import day_events
from ..extensions import db
from ..models import Absence, Attendance, Event
from ..models.event import MOODS
from ..notify import notify

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
    context["attendance"] = db.session.scalar(
        select(Attendance).where(Attendance.child_id == child.id, Attendance.day == day)
    )
    context["absence"] = db.session.scalar(
        select(Absence).where(
            Absence.child_id == child.id,
            Absence.start_date <= day,
            Absence.end_date >= day,
            Absence.cancelled_at.is_(None),
        )
    )
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
    if current_user.is_staff:
        # Staff cannot acknowledge on a family's behalf.
        abort(403)
    if event.acknowledged_at is None:
        event.acknowledged_at = timeutil.now()
        event.acknowledged_by_id = current_user.id
        notify(
            access.staff_for_child(child),
            "acknowledged",
            f"{current_user.name} acknowledged the {event.label.lower()} report for "
            f"{child.display_name}",
            url_for(
                "timeline.child_day", child_id=child.id, day=timeutil.fmt_isoday(event.occurred_at)
            ),
            child=child,
        )
        db.session.commit()
        flash("Thank you, the staff can see that you have read it.", "success")
    return redirect(
        url_for("timeline.child_day", child_id=child.id, day=timeutil.fmt_isoday(event.occurred_at))
        + f"#event-{event.id}"
    )


@bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id: int):
    if not current_user.is_staff:
        abort(404)
    event = db.session.get(Event, event_id)
    if event is None or event.deleted_at is not None:
        abort(404)
    child = access.child_or_404(event.child_id)
    back = url_for(
        "timeline.child_day", child_id=child.id, day=timeutil.fmt_isoday(event.occurred_at)
    )
    errors = []
    if request.method == "POST":
        note = (request.form.get("note") or "").strip() or None
        clock = timeutil.parse_clock(request.form.get("at"))
        visibility = "staff" if request.form.get("visibility") == "staff" else "parents"
        if event.needs_ack:
            visibility = "parents"
        if clock is not None:
            day = timeutil.local(event.occurred_at).date()
            event.occurred_at = timeutil.at(day, clock)
        if event.kind == "mood" and request.form.get("mood") in dict(MOODS):
            event.details = {**event.details, "mood": request.form["mood"]}
        if event.kind == "nap":
            end = timeutil.parse_clock(request.form.get("ended"))
            if end is not None:
                ended = timeutil.at(timeutil.local(event.occurred_at).date(), end)
                if ended <= event.occurred_at:
                    errors.append("The nap has to end after it started.")
                else:
                    event.ended_at = ended
        if not errors:
            event.note = note
            event.visibility = visibility
            event.updated_at = timeutil.now()
            event.updated_by_id = current_user.id
            db.session.commit()
            flash("Saved.", "success")
            return redirect(back)
        db.session.rollback()
    return render_template(
        "timeline/edit.html", event=event, child=child, back=back, moods=MOODS, errors=errors
    )


@bp.post("/events/<int:event_id>/delete")
@login_required
def delete_event(event_id: int):
    if not current_user.is_staff:
        abort(404)
    event = db.session.get(Event, event_id)
    if event is None or event.deleted_at is not None:
        abort(404)
    child = access.child_or_404(event.child_id)
    event.deleted_at = timeutil.now()
    event.updated_by_id = current_user.id
    db.session.commit()
    flash("Removed from the diary.", "success")
    return redirect(
        url_for("timeline.child_day", child_id=child.id, day=timeutil.fmt_isoday(event.occurred_at))
    )
