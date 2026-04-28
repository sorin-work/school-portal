from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Attendance(db.Model):
    """One row per child per day they were in, with who brought and collected them."""

    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    day: Mapped[date] = mapped_column(Date, index=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_in_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # Who collected the child: a guardian, a collector or a name typed in.
    collected_by: Mapped[str | None] = mapped_column(String(120))
    collector_id: Mapped[int | None] = mapped_column(
        ForeignKey("collectors.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)

    child = relationship("Child")
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    checked_out_by = relationship("User", foreign_keys=[checked_out_by_id])
