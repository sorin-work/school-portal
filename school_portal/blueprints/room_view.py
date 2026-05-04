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
from ..models import Absence, Child, CurriculumArea, Event, EventMedia, Room
from ..models.event import AMOUNTS, MEALS, MOODS, NAPPY, TOILET
from ..uploads import UploadError, save_image

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
    today = timeutil.today()
    absent = {
        a.child_id
        for a in db.session.scalars(
            select(Absence).where(
                Absence.child_id.in_([c.id for c in children]),
                Absence.start_date <= today,
                Absence.end_date >= today,
                Absence.cancelled_at.is_(None),
            )
        )
    }
    skipped = [c for c in children if c.id in absent]
    children = [c for c in children if c.id not in absent]
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
    if skipped:
        names = ", ".join(c.short_name for c in skipped)
        flash(f"Left out because they are reported absent today: {names}.", "info")
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
        files = [f for f in request.files.getlist("photos") if f and f.filename]
        if len(files) > 4:
            errors.append("Attach at most four photos.")
        if files:
            refused = [c.short_name for c in chosen if c.photo_consent == "none"]
            if refused:
                errors.append(
                    "No photo consent for " + ", ".join(refused) + ". Leave them out of the "
                    "photo, or save the observation without photos."
                )
        media = []
        if not errors:
            try:
                media = [save_image(f, purpose="photo", user_id=current_user.id) for f in files]
            except UploadError as exc:
                errors.append(str(exc))
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
                for item in media:
                    event.photos.append(EventMedia(media=item))
            db.session.commit()
            flash(f"Observation saved for {len(chosen)} children.", "success")
            return redirect(url_for(".show", room_id=room.id))
        db.session.rollback()
    return render_template(
        "rooms/observe.html", room=room, children=children, areas=areas, errors=errors
    )


@bp.route("/<int:room_id>/incident", methods=["GET", "POST"])
@staff_required
def incident(room_id: int):
    """An incident or an accident. Parents always see it and have to acknowledge it."""
    room = room_or_404(room_id)
    children = room_children(room)
    errors: list[str] = []
    form = request.form
    if request.method == "POST":
        child_id = form.get("child_id", type=int)
        child = next((c for c in children if c.id == child_id), None)
        kind = form.get("kind")
        what = (form.get("what") or "").strip()
        action = (form.get("action_taken") or "").strip()
        if child is None:
            errors.append("Choose the child.")
        if kind not in ("incident", "accident"):
            errors.append("Choose incident or accident.")
        if not what:
            errors.append("Say what happened.")
        if not action:
            errors.append("Say what was done about it.")
        if not errors:
            details = {
                "what": what,
                "action_taken": action,
                "injury": (form.get("injury") or "").strip(),
                "witness": (form.get("witness") or "").strip(),
            }
            event = log_event(child, room, kind, when_from_form(), details, what, "parents")
            event.needs_ack = True
            db.session.flush()
            db.session.commit()
            flash(
                f"{event.label} recorded. The family has been asked to acknowledge it.", "success"
            )
            return redirect(url_for(".show", room_id=room.id))
    return render_template("rooms/incident.html", room=room, children=children, errors=errors)
