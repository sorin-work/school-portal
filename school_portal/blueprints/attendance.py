"""The register: who is in, who collected them, and absences reported ahead."""

from flask import Blueprint, render_template
from flask_login import current_user

from .. import timeutil
from ..decorators import staff_required
from ..events import child_days
from ..extensions import db
from ..models import Attendance
from .room_view import child_in_room, room_children, room_or_404

bp = Blueprint("attendance", __name__)


@bp.get("/rooms/<int:room_id>/register")
@staff_required
def register(room_id: int):
    room = room_or_404(room_id)
    children = room_children(room)
    day = timeutil.today()
    days = child_days(children, day)
    return render_template("attendance/register.html", room=room, children=children, days=days)


def _row_response(room, child):
    day = child_days([child], timeutil.today())[child.id]
    return render_template("attendance/_row.html", room=room, child=child, day=day)


@bp.post("/rooms/<int:room_id>/children/<int:child_id>/check-in")
@staff_required
def check_in(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    today = timeutil.today()
    db.session.add(
        Attendance(
            child_id=child.id,
            room_id=room.id,
            day=today,
            checked_in_at=timeutil.now(),
            checked_in_by_id=current_user.id,
        )
    )
    db.session.commit()
    return _row_response(room, child)
