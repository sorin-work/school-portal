from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func, select

from .. import access, timeutil
from ..extensions import db
from ..models import Attendance, Child, Event

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@login_required
def home():
    if current_user.is_staff:
        return render_template("dashboard/staff.html", **_staff_context())
    return render_template("dashboard/parent.html", **_parent_context())


def _staff_context() -> dict:
    context: dict = {}
    rooms = access.rooms_for(current_user)
    context["rooms"] = rooms
    today = timeutil.today()
    counts = dict(
        db.session.execute(
            select(Attendance.room_id, func.count())
            .where(Attendance.day == today, Attendance.checked_out_at.is_(None))
            .group_by(Attendance.room_id)
        ).all()
    )
    context["present"] = counts
    sizes = dict(
        db.session.execute(
            access.children_query(current_user)
            .with_only_columns(Child.room_id, func.count())
            .group_by(Child.room_id)
            .order_by(None)
        ).all()
    )
    context["sizes"] = sizes
    scope = access.children_query(current_user).with_only_columns(Child.id).order_by(None)
    context["awaiting_ack"] = list(
        db.session.scalars(
            select(Event)
            .where(
                Event.child_id.in_(scope),
                Event.needs_ack,
                Event.acknowledged_at.is_(None),
                Event.deleted_at.is_(None),
            )
            .order_by(Event.occurred_at.desc())
            .limit(20)
        )
    )
    return context


def _parent_context() -> dict:
    children = list(db.session.scalars(access.children_query(current_user, include_left=True)))
    context: dict = {"children": children}
    ids = [c.id for c in children]
    context["awaiting_ack"] = (
        list(
            db.session.scalars(
                select(Event).where(
                    Event.child_id.in_(ids),
                    Event.needs_ack,
                    Event.acknowledged_at.is_(None),
                    Event.deleted_at.is_(None),
                    Event.visibility == "parents",
                )
            )
        )
        if ids
        else []
    )
    from .notices import notices_for

    context["notices"] = notices_for(current_user)[:3]
    from .calendar import events_for

    context["upcoming"] = [e for e in events_for(current_user) if e.starts_at >= timeutil.now()][:4]
    return context
