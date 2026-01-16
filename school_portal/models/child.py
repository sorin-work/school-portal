from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Child(db.Model):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    preferred_name: Mapped[str | None] = mapped_column(String(80))
    date_of_birth: Mapped[date] = mapped_column(Date)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    key_person_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    start_date: Mapped[date | None] = mapped_column(Date)
    dietary_needs: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    share_medical_with_parents: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room = relationship("Room")
    key_person = relationship("User")

    @property
    def display_name(self) -> str:
        return f"{self.preferred_name or self.first_name} {self.last_name}"

    @property
    def short_name(self) -> str:
        return f"{self.preferred_name or self.first_name} {self.last_name[:1]}."

    @property
    def initials(self) -> str:
        return f"{(self.preferred_name or self.first_name)[:1]}{self.last_name[:1]}".upper()

    @property
    def has_allergies(self) -> bool:
        return bool(self.allergies and self.allergies.strip())

    def age_on(self, day: date) -> str:
        months = (day.year - self.date_of_birth.year) * 12 + day.month - self.date_of_birth.month
        if day.day < self.date_of_birth.day:
            months -= 1
        if months < 24:
            return f"{months} months"
        return (
            f"{months // 12} years {months % 12} months" if months % 12 else f"{months // 12} years"
        )
