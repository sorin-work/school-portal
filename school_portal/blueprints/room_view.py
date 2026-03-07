"""The room view: a tablet-friendly page for logging the day as it happens."""

import uuid
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from .. import access, timeutil
from ..decorators import staff_required
from ..events import child_days, log_event
from ..extensions import db
from ..models import Child, CurriculumArea, Event, Room
from ..models.event import AMOUNTS, MEALS, MOODS, NAPPY, TOILET

bp = Blueprint("room_view", __name__, url_prefix="/rooms")


def room_or_404(room_id: int) -> Room:
    room = db.session.get(Room, room_id)
    if room is None or room.id not in access.staff_room_ids(current_user):
        abort(404)
    return room


def room_children(room: Room) -> list[Child]:
    query = select(Child).where(Child.room_id == room.id).order_by(Child.first_name)
    return list(db.session.scalars(query))


def child_in_room(room: Room, child_id: int) -> Child:
    child = db.session.get(Child, child_id)
    if child is None or child.room_id != room.id:
        abort(404)
    return child


def when_from_form(field: str = "at") -> datetime:
    """The time typed on the form, today, or now when it is empty."""
    clock = timeutil.parse_clock(request.form.get(field))
    if clock is None:
        return timeutil.now()
    return timeutil.at(timeutil.today(), clock)


def visibility_from_form() -> str:
    return "staff" if request.form.get("visibility") == "staff" else "parents"


@bp.get("/")
@staff_required
def index():
    rooms = access.rooms_for(current_user)
    if len(rooms) == 1:
        return redirect(url_for(".show", room_id=rooms[0].id))
    return render_template("rooms/index.html", rooms=rooms)


@bp.get("/<int:room_id>")
@staff_required
def show(room_id: int):
    room = room_or_404(room_id)
    children = room_children(room)
    days = child_days(children, timeutil.today())
    return render_template(
        "rooms/show.html",
        room=room,
        children=children,
        days=days,
        meals=MEALS,
        amounts=AMOUNTS,
    )


@bp.get("/<int:room_id>/children/<int:child_id>/panel")
@staff_required
def panel(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    day = child_days([child], timeutil.today())[child.id]
    return render_template(
        "rooms/_panel.html",
        room=room,
        child=child,
        day=day,
        nappy=NAPPY,
        toilet=TOILET,
        moods=MOODS,
    )


def _tile_response(room: Room, child: Child, message: str):
    day = child_days([child], timeutil.today())[child.id]
    return render_template(
        "rooms/_logged.html",
        room=room,
        child=child,
        day=day,
        message=message,
        nappy=NAPPY,
        toilet=TOILET,
        moods=MOODS,
    )


@bp.post("/<int:room_id>/children/<int:child_id>/log")
@staff_required
def quick_log(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    kind = request.form.get("kind", "")
    when = when_from_form()
    visibility = visibility_from_form()
    note = (request.form.get("note") or "").strip() or None
    if kind == "nappy" and room.is_nursery:
        value = request.form.get("value", "")
        if value not in dict(NAPPY):
            abort(400)
        log_event(child, room, "nappy", when, {"type": value}, note, visibility)
        message = "Nappy logged"
    elif kind == "toilet":
        value = request.form.get("value", "")
        if value not in dict(TOILET):
            abort(400)
        log_event(child, room, "toilet", when, {"result": value}, note, visibility)
        message = "Toilet logged"
    elif kind == "mood":
        value = request.form.get("value", "")
        if value not in dict(MOODS):
            abort(400)
        log_event(child, room, "mood", when, {"mood": value}, note, visibility)
        message = "Mood logged"
    elif kind == "nap" and room.is_nursery:
        if child_days([child], timeutil.today())[child.id].open_nap is not None:
            return _tile_response(room, child, "Already asleep")
        log_event(child, room, "nap", when, {}, note, visibility)
        message = "Nap started"
    elif kind == "note":
        if not note:
            return _tile_response(room, child, "Write the note first")
        log_event(child, room, "note", when, {}, note, visibility)
        message = "Note added"
    else:
        abort(400)
    db.session.commit()
    return _tile_response(room, child, message)


@bp.post("/<int:room_id>/naps/<int:event_id>/end")
@staff_required
def end_nap(room_id: int, event_id: int):
    room = room_or_404(room_id)
    event = db.session.get(Event, event_id)
    if event is None or event.kind != "nap" or event.deleted_at is not None:
        abort(404)
    child = child_in_room(room, event.child_id)
    if event.ended_at is not None:
        return _tile_response(room, child, "That nap was already ended")
    end = when_from_form()
    if end <= event.occurred_at:
        return _tile_response(room, child, "The end must be after the start")
    event.ended_at = end
    event.updated_at = timeutil.now()
    event.updated_by_id = current_user.id
    db.session.commit()
    return _tile_response(room, child, "Awake")


@bp.post("/<int:room_id>/bulk")
@staff_required
def bulk(room_id: int):
    """Log the same thing for several children, for example lunch."""
    room = room_or_404(room_id)
    kind = request.form.get("kind")
    ids = {int(v) for v in request.form.getlist("child_ids") if v.isdigit()}
    children = [c for c in room_children(room) if c.id in ids]
    if not children:
        flash("Choose at least one child.", "error")
        return redirect(url_for(".show", room_id=room.id))
    when = when_from_form()
    note = (request.form.get("note") or "").strip() or None
    visibility = visibility_from_form()
    batch = uuid.uuid4().hex
    if kind == "meal":
        meal = request.form.get("meal")
        if meal not in MEALS:
            abort(400)
        menu = (request.form.get("menu") or "").strip()[:200]
        default_amount = request.form.get("amount", "all")
        for child in children:
            # A per-child amount overrides the one for everyone.
            amount = request.form.get(f"amount_{child.id}") or default_amount
            if amount not in dict(AMOUNTS):
                abort(400)
            details = {"meal": meal, "amount": amount}
            if menu:
                details["menu"] = menu
            log_event(child, room, "meal", when, details, note, visibility, batch=batch)
        label = meal
    elif kind == "activity":
        title = (request.form.get("title") or "").strip()[:200]
        if not title:
            flash("Give the activity a title.", "error")
            return redirect(url_for(".show", room_id=room.id))
        for child in children:
            log_event(
                child, room, "activity", when, {"title": title}, note, visibility, batch=batch
            )
        label = title
    else:
        abort(400)
    db.session.commit()
    flash(f"Logged {label} for {len(children)} children.", "success")
    return redirect(url_for(".show", room_id=room.id))


@bp.route("/<int:room_id>/observe", methods=["GET", "POST"])
@staff_required
def observe(room_id: int):
    """A learning observation for one or more children, with photos."""
    room = room_or_404(room_id)
    children = room_children(room)
    areas = list(db.session.scalars(select(CurriculumArea).order_by(CurriculumArea.sort_order)))
    errors: list[str] = []
    if request.method == "POST":
        ids = {int(v) for v in request.form.getlist("child_ids") if v.isdigit()}
        chosen = [c for c in children if c.id in ids]
        note = (request.form.get("note") or "").strip()
        next_steps = (request.form.get("next_steps") or "").strip()
        area_id = request.form.get("area_id", type=int)
        if area_id and area_id not in {a.id for a in areas}:
            area_id = None
        if not chosen:
            errors.append("Choose the children the observation is about.")
        if not note:
            errors.append("Describe what you saw.")
        if not errors:
            batch = uuid.uuid4().hex
            when = when_from_form()
            details = {"next_steps": next_steps} if next_steps else {}
            for child in chosen:
                event = log_event(
                    child,
                    room,
                    "observation",
                    when,
                    details,
                    note,
                    visibility_from_form(),
                    batch=batch,
                )
                event.area_id = area_id
            db.session.commit()
            flash(f"Observation saved for {len(chosen)} children.", "success")
            return redirect(url_for(".show", room_id=room.id))
        db.session.rollback()
    return render_template(
        "rooms/observe.html", room=room, children=children, areas=areas, errors=errors
    )
