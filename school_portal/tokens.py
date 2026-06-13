"""Single-use password links for invites and resets."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import func, select

from . import timeutil
from .extensions import db
from .models import PasswordToken, User

LIFETIME = {"reset": timedelta(hours=1), "invite": timedelta(days=7)}
RESETS_PER_HOUR = 3


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(user: User, purpose: str) -> str:
    token = secrets.token_urlsafe(32)
    db.session.add(
        PasswordToken(
            user_id=user.id,
            token_hash=_hash(token),
            purpose=purpose,
            expires_at=timeutil.now() + LIFETIME[purpose],
        )
    )
    return token


def find(token: str) -> PasswordToken | None:
    record = db.session.scalar(
        select(PasswordToken).where(PasswordToken.token_hash == _hash(token))
    )
    if record is None or record.used_at is not None or record.expires_at <= timeutil.now():
        return None
    if not record.user.active:
        return None
    return record


def may_send_reset(user: User) -> bool:
    since = timeutil.now() - timedelta(hours=1)
    sent = db.session.scalar(
        select(func.count()).where(
            PasswordToken.user_id == user.id,
            PasswordToken.purpose == "reset",
            PasswordToken.created_at >= since,
        )
    )
    return (sent or 0) < RESETS_PER_HOUR


def revoke_others(user: User, keep: PasswordToken) -> None:
    for other in db.session.scalars(
        select(PasswordToken).where(
            PasswordToken.user_id == user.id,
            PasswordToken.used_at.is_(None),
            PasswordToken.id != keep.id,
        )
    ):
        other.used_at = timeutil.now()
