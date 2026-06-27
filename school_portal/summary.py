"""The daily summary email to families.

At the time set under Settings, the worker queues one "daily_summary" job for
the day. That job writes one email per parent or carer, covering each of their
children who had something in the diary, and only what families may see.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import select

from . import jobs, settings
from .events import day_events
from .extensions import db
from .mail import queue_email
from .models import Child, Guardian, User


def build_summaries(day: date) -> dict[int, list[tuple[Child, list]]]:
    """user id -> [(child, events)] for everyone who should get an email."""
    links = db.session.execute(
        select(Guardian, Child, User)
        .join(Child, Child.id == Guardian.child_id)
        .join(User, User.id == Guardian.user_id)
        .where(
            Guardian.access.in_(["full", "read_only"]),
            Guardian.receives_summary,
            User.active,
            User.password_hash.is_not(None),
        )
    ).all()
    children = {child.id: child for _, child, _ in links}
    events_by_child = defaultdict(list)
    for event in day_events(list(children), day) if children else []:
        events_by_child[event.child_id].append(event)
    result: dict[int, list] = defaultdict(list)
    for _, child, user in links:
        if events_by_child.get(child.id):
            result[user.id].append((child, events_by_child[child.id]))
    return result


@jobs.handler("daily_summary")
def send_daily_summary(payload: dict) -> None:
    day = date.fromisoformat(payload["day"])
    school_name = settings.get("school_name")
    for user_id, items in build_summaries(day).items():
        user = db.session.get(User, user_id)
        names = " and ".join(child.preferred_name or child.first_name for child, _ in items)
        queue_email(
            user.email,
            f"{names}'s day at {school_name}",
            "email/summary.txt",
            user=user,
            items=items,
            day=day,
            school_name=school_name,
        )
