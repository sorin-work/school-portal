from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .. import access
from ..extensions import db

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
    return context


def _parent_context() -> dict:
    children = list(db.session.scalars(access.children_query(current_user, include_left=True)))
    context: dict = {"children": children}
    return context
