from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select, update

from .. import timeutil
from ..extensions import db
from ..models import Notification

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


def unread_count(user) -> int:
    return (
        db.session.scalar(
            select(func.count()).where(
                Notification.user_id == user.id, Notification.read_at.is_(None)
            )
        )
        or 0
    )


@bp.get("/")
@login_required
def index():
    items = list(
        db.session.scalars(
            select(Notification)
            .where(Notification.user_id == current_user.id)
            .order_by(Notification.id.desc())
            .limit(100)
        )
    )
    return render_template("notifications/index.html", items=items)


@bp.get("/count")
@login_required
def count():
    return render_template(
        "notifications/_count.html", unread_notifications=unread_count(current_user)
    )


@bp.get("/<int:notification_id>")
@login_required
def open_one(notification_id: int):
    item = db.session.get(Notification, notification_id)
    if item is None or item.user_id != current_user.id:
        return redirect(url_for(".index"))
    if item.read_at is None:
        item.read_at = timeutil.now()
        db.session.commit()
    target = item.url or url_for(".index")
    if not target.startswith("/") or target.startswith("//"):
        target = url_for(".index")
    return redirect(target)


@bp.post("/read")
@login_required
def mark_all_read():
    db.session.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=timeutil.now())
    )
    db.session.commit()
    if request.headers.get("HX-Request"):
        return render_template("notifications/_count.html", unread_notifications=0)
    return redirect(url_for(".index"))
