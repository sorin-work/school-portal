from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

EVENT_KINDS = [
    ("event", "Event"),
    ("trip", "Trip"),
    ("closure", "Closure"),
    ("meeting", "Parents' meeting"),
]

school_event_rooms = Table(
    "school_event_rooms",
    db.metadata,
    Column("school_event_id", ForeignKey("school_events.id", ondelete="CASCADE"), primary_key=True),
    Column("room_id", ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
)


class SchoolEvent(db.Model):
    """A date on the school calendar: a trip, a closure, a sports day."""

    __tablename__ = "school_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), default="event")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str | None] = mapped_column(String(160))
    rsvp_required: Mapped[bool] = mapped_column(default=False)
    consent_required: Mapped[bool] = mapped_column(default=False)
    consent_text: Mapped[str | None] = mapped_column(Text)
    respond_by: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rooms = relationship("Room", secondary=school_event_rooms)

    @property
    def kind_label(self) -> str:
        return dict(EVENT_KINDS).get(self.kind, self.kind)

    @property
    def asks_parents(self) -> bool:
        return self.rsvp_required or self.consent_required


class Rsvp(db.Model):
    """A family's answer for one child, with trip consent when it is asked for."""

    __tablename__ = "rsvps"
    __table_args__ = (db.UniqueConstraint("school_event_id", "child_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_event_id: Mapped[int] = mapped_column(ForeignKey("school_events.id", ondelete="CASCADE"))
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    attending: Mapped[bool]
    consent_given: Mapped[bool] = mapped_column(default=False)
    # The parent types their name as a signature on the consent form.
    signed_name: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    responded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    child = relationship("Child")
    responded_by = relationship("User")
    school_event = relationship("SchoolEvent")
