from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

notice_rooms = Table(
    "notice_rooms",
    db.metadata,
    Column("notice_id", ForeignKey("notices.id", ondelete="CASCADE"), primary_key=True),
    Column("room_id", ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
)


class Notice(db.Model):
    """A notice for every family, or for the families of some rooms."""

    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_on: Mapped[date | None] = mapped_column(Date)
    pinned: Mapped[bool] = mapped_column(default=False)

    author = relationship("User")
    # No rooms means the whole school.
    rooms = relationship("Room", secondary=notice_rooms)
