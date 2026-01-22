from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import access
from ..extensions import db
from ..models import Child

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
    sizes = dict(
        db.session.execute(
            access.children_query(current_user)
            .with_only_columns(Child.room_id, func.count())
            .group_by(Child.room_id)
            .order_by(None)
        ).all()
    )
    context["sizes"] = sizes
    return context


def _parent_context() -> dict:
    children = list(db.session.scalars(access.children_query(current_user, include_left=True)))
    context: dict = {"children": children}
    return context
