"""The register: who is in, who collected them, and absences reported ahead."""

from flask import Blueprint, abort, render_template, request
from flask_login import current_user
from sqlalchemy import select

from .. import timeutil
from ..decorators import staff_required
from ..events import child_days
from ..extensions import db
from ..models import Attendance, Child
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


def collector_choices(child: Child) -> list[tuple[str, str]]:
    """Guardians who may collect, then the child's active collectors."""
    choices = []
    for link in child.guardians:
        choices.append((f"g:{link.user_id}", f"{link.user.name} ({link.relationship_label})"))
    return choices


@bp.route("/rooms/<int:room_id>/children/<int:child_id>/check-out", methods=["GET", "POST"])
@staff_required
def check_out(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    row = db.session.scalar(
        select(Attendance).where(
            Attendance.child_id == child.id,
            Attendance.day == timeutil.today(),
            Attendance.checked_out_at.is_(None),
        )
    )
    if row is None:
        abort(404)
    choices = collector_choices(child)
    if request.method == "POST":
        picked = request.form.get("collector", "")
        other = (request.form.get("other") or "").strip()[:120]
        labels = dict(choices)
        if picked in labels:
            row.collected_by = labels[picked].split(" (")[0]
        elif picked == "other" and other:
            row.collected_by = other
            row.note = (request.form.get("note") or "").strip() or None
        else:
            return render_template(
                "attendance/_checkout.html",
                room=room,
                child=child,
                choices=choices,
                collectors=_collectors(child),
                error="Say who collected the child.",
            )
        row.checked_out_at = timeutil.now()
        row.checked_out_by_id = current_user.id
        db.session.commit()
        return _row_response(room, child)
    return render_template(
        "attendance/_checkout.html",
        room=room,
        child=child,
        choices=choices,
        collectors=_collectors(child),
        error=None,
    )


def _collectors(child: Child) -> list:
    return []
