import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


def new_media_id() -> str:
    return uuid.uuid4().hex


class Media(db.Model):
    """An uploaded image, stored under UPLOAD_DIR with a random name.

    Files are never served from a static path. Every request goes through
    media.show, which checks who may see the file.
    """

    __tablename__ = "media"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_media_id)
    # "photo" for observation photos, "collector" for collector photos.
    purpose: Mapped[str] = mapped_column(String(16), default="photo")
    content_type: Mapped[str] = mapped_column(String(40))
    size: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    stored_name: Mapped[str] = mapped_column(String(80))
    thumb_name: Mapped[str] = mapped_column(String(80))
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploaded_by = relationship("User")
