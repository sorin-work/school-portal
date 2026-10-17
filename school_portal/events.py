"""Creating events and reading a child's day."""

from dataclasses import dataclass, field
from datetime import date, datetime

from flask_login import current_user
from sqlalchemy import select

from . import timeutil
from .extensions import db
from .models import Absence, Attendance, Child, Event, Room


def log_event(
    child: Child,
    room: Room | None,
    kind: str,
    when: datetime,
    details: dict | None = None,
    note: str | None = None,
    visibility: str = "parents",
    *,
    batch: str | None = None,
) -> Event:
    event = Event(
        child_id=child.id,
        room_id=room.id if room is not None else child.room_id,
        kind=kind,
        occurred_at=when,
        details=details or {},
        note=note,
        visibility=visibility,
        batch_id=batch,
        created_by_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(event)
    return event


@dataclass
class ChildDay:
    """What the room view needs to know about one child today."""

    events: list[Event] = field(default_factory=list)
    open_nap: Event | None = None
    attendance: "Attendance | None" = None
    absence: "Absence | None" = None

    @property
    def last(self) -> Event | None:
        return self.events[-1] if self.events else None

    def latest(self, kind: str) -> Event | None:
        for event in reversed(self.events):
            if event.kind == kind:
                return event
        return None

    @property
    def present(self) -> bool:
        return self.attendance is not None and self.attendance.checked_out_at is None

    @property
    def gone_home(self) -> bool:
        return self.attendance is not None and self.attendance.checked_out_at is not None


def day_events(child_ids: list[int], day: date) -> list[Event]:
    start, end = timeutil.day_bounds(day)
    return list(
        db.session.scalars(
            select(Event)
            .where(
                Event.child_id.in_(child_ids),
                Event.occurred_at >= start,
                Event.occurred_at < end,
                Event.deleted_at.is_(None),
            )
            .order_by(Event.occurred_at, Event.id)
        )
    )


def child_days(children: list[Child], day: date) -> dict[int, ChildDay]:
    days = {c.id: ChildDay() for c in children}
    if not children:
        return days
    ids = list(days)
    for event in day_events(ids, day):
        state = days[event.child_id]
        state.events.append(event)
        if event.kind == "nap" and event.ended_at is None:
            state.open_nap = event
    for row in db.session.scalars(
        select(Attendance).where(Attendance.child_id.in_(ids), Attendance.day == day)
    ):
        days[row.child_id].attendance = row
    for absence in db.session.scalars(
        select(Absence).where(
            Absence.child_id.in_(ids),
            Absence.start_date <= day,
            Absence.end_date >= day,
            Absence.cancelled_at.is_(None),
        )
    ):
        days[absence.child_id].absence = absence
    return days
