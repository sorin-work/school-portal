from datetime import datetime
from enum import StrEnum

from flask import current_app, has_app_context
from flask_login import UserMixin
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class Role(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"
    PARENT = "parent"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16), default=Role.PARENT)
    phone: Mapped[str | None] = mapped_column(String(40))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(default=True)
    session_version: Mapped[int] = mapped_column(default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def set_password(self, password: str) -> None:
        method = "scrypt"
        if has_app_context():
            method = current_app.config.get("PASSWORD_HASH_METHOD", method)
        self.password_hash = generate_password_hash(password, method=method)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        # The version is part of the id kept in the session cookie, so raising
        # it signs the user out everywhere.
        return f"{self.id}:{self.session_version}"

    @property
    def is_active(self) -> bool:
        return self.active

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_staff(self) -> bool:
        """Staff and administrators both work in the rooms."""
        return self.role in (Role.STAFF, Role.ADMIN)

    @property
    def is_parent(self) -> bool:
        return self.role == Role.PARENT

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0]

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} {self.role}>"
