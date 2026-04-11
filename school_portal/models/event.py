from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

# kind -> (label, colour used for the badge)
KINDS = {
    "activity": ("Activity", "sky"),
    "meal": ("Meal", "amber"),
    "nap": ("Nap", "indigo"),
    "nappy": ("Nappy", "stone"),
    "toilet": ("Toilet", "stone"),
    "mood": ("Mood", "pink"),
    "observation": ("Learning", "emerald"),
    "incident": ("Incident", "orange"),
    "accident": ("Accident", "red"),
    "note": ("Note", "slate"),
}

# Kinds that only make sense in nursery rooms.
NURSERY_ONLY = {"nap", "nappy"}
# Kinds a parent has to acknowledge, always visible to parents.
NEEDS_ACK = {"incident", "accident"}

MEALS = ["breakfast", "snack", "lunch", "tea"]
AMOUNTS = [("all", "All of it"), ("most", "Most"), ("some", "Some"), ("none", "None")]
NAPPY = [("wet", "Wet"), ("dirty", "Dirty"), ("dry", "Dry"), ("cream", "Cream applied")]
TOILET = [("wee", "Wee"), ("poo", "Poo"), ("tried", "Tried")]
MOODS = [
    ("happy", "Happy"),
    ("settled", "Settled"),
    ("tired", "Tired"),
    ("unsettled", "Unsettled"),
    ("upset", "Upset"),
]


class Event(db.Model):
    """One thing that happened to one child: a meal, a nap, an observation."""

    __tablename__ = "events"
    __table_args__ = (
        db.Index("ix_events_child_occurred", "child_id", "occurred_at"),
        db.Index("ix_events_room_occurred", "room_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    note: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(8), default="parents")
    # Events logged together ("everyone had lunch") share a batch id.
    batch_id: Mapped[str | None] = mapped_column(String(32), index=True)
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("curriculum_areas.id", ondelete="SET NULL")
    )
    needs_ack: Mapped[bool] = mapped_column(default=False, server_default="false")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    child = relationship("Child")
    room = relationship("Room")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    area = relationship("CurriculumArea")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    photos: Mapped[list["EventMedia"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    @property
    def label(self) -> str:
        return KINDS.get(self.kind, (self.kind.title(), "slate"))[0]

    @property
    def colour(self) -> str:
        return KINDS.get(self.kind, ("", "slate"))[1]

    @property
    def staff_only(self) -> bool:
        return self.visibility == "staff"

    @property
    def in_progress(self) -> bool:
        return self.kind == "nap" and self.ended_at is None

    def summary(self) -> str:
        """A short line for lists and the daily email."""
        d = self.details or {}
        if self.kind == "meal":
            amount = dict(AMOUNTS).get(d.get("amount", ""), "")
            menu = f" ({d['menu']})" if d.get("menu") else ""
            return f"{d.get('meal', 'meal').title()}{menu}: {amount.lower() or 'eaten'}"
        if self.kind == "nap":
            if self.ended_at is None:
                return "Asleep"
            minutes = int((self.ended_at - self.occurred_at).total_seconds() // 60)
            return (
                f"Slept for {minutes // 60}h {minutes % 60:02d}m"
                if minutes >= 60
                else (f"Slept for {minutes} minutes")
            )
        if self.kind == "nappy":
            return "Nappy: " + dict(NAPPY).get(d.get("type", ""), "changed").lower()
        if self.kind == "toilet":
            return "Toilet: " + dict(TOILET).get(d.get("result", ""), "visit").lower()
        if self.kind == "mood":
            return "Feeling " + dict(MOODS).get(d.get("mood", ""), "fine").lower()
        if d.get("title"):
            return d["title"]
        return (self.note or self.label)[:80]


class CurriculumArea(db.Model):
    """An area of learning, for example from the EYFS or a key stage."""

    __tablename__ = "curriculum_areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    framework: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(default=0)


class EventMedia(db.Model):
    __tablename__ = "event_media"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[str] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )

    event: Mapped[Event] = relationship(back_populates="photos")
    media = relationship("Media")
