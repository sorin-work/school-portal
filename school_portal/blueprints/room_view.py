"""The room view: a tablet-friendly page for logging the day as it happens."""

from datetime import datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from .. import access, timeutil
from ..decorators import staff_required
from ..events import child_days
from ..extensions import db
from ..models import Child, Room
from ..models.event import AMOUNTS, MEALS

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
