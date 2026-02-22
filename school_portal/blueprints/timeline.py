"""A child's diary, one day at a time."""

from datetime import timedelta

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from .. import access, timeutil
from ..events import day_events

bp = Blueprint("timeline", __name__)


def visible_events(child, day):
    events = day_events([child.id], day)
    if current_user.is_staff:
        return events
    return [e for e in events if e.visibility == "parents"]


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
        **context,
    )
