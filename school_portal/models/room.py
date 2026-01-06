from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Room(db.Model):
    """A nursery room or a school class."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    # "nursery" rooms log naps and nappies; "class" rooms do not show them.
    kind: Mapped[str] = mapped_column(String(16), default="nursery")
    age_range: Mapped[str | None] = mapped_column(String(40))
    capacity: Mapped[int | None]
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    staff: Mapped[list["RoomStaff"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    @property
    def is_nursery(self) -> bool:
        return self.kind == "nursery"

    @property
    def leads(self):
        return [s.user for s in self.staff if s.is_lead]


class RoomStaff(db.Model):
    __tablename__ = "room_staff"

    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    is_lead: Mapped[bool] = mapped_column(default=False)

    room: Mapped[Room] = relationship(back_populates="staff")
    user = relationship("User")
