from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

PHOTO_CONSENT_CHOICES = [
    ("none", "No photos shared"),
    ("own", "Photos shared with this child's own family only"),
    ("group", "May appear in group photos other families see"),
]
ACCESS_CHOICES = [
    ("full", "Full access"),
    ("read_only", "Timeline only (no messages, forms or absence reports)"),
    ("none", "No access"),
]


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
    photo_consent: Mapped[str] = mapped_column(String(8), default="none", server_default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room = relationship("Room")
    key_person = relationship("User")
    guardians: Mapped[list["Guardian"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )

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


class Guardian(db.Model):
    """The link between a parent or carer account and a child."""

    __tablename__ = "guardians"
    __table_args__ = (db.UniqueConstraint("child_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    relationship_label: Mapped[str] = mapped_column("relationship", String(40), default="Parent")
    access: Mapped[str] = mapped_column(String(16), default="full")
    receives_summary: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    child: Mapped[Child] = relationship(back_populates="guardians")
    user = relationship("User", foreign_keys=[user_id])

    @property
    def can_view(self) -> bool:
        return self.access in ("full", "read_only")

    @property
    def can_act(self) -> bool:
        """Send messages, report absences, answer forms."""
        return self.access == "full"
