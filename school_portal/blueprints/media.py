"""Serving uploaded images, only to people allowed to see them."""

from flask import Blueprint, abort, send_file
from flask_login import current_user, login_required
from sqlalchemy import select

from .. import access, photos, uploads
from ..extensions import db
from ..models import Child, Collector, Event, EventMedia, Media

bp = Blueprint("media", __name__, url_prefix="/media")


def may_see(media: Media) -> bool:
    if media.purpose == "collector":
        collector = db.session.scalar(select(Collector).where(Collector.photo_id == media.id))
        return collector is not None and access.can_view_child(current_user, collector.child)
    rows = db.session.execute(
        select(Event, Child)
        .join(EventMedia, EventMedia.event_id == Event.id)
        .join(Child, Child.id == Event.child_id)
        .where(EventMedia.media_id == media.id, Event.deleted_at.is_(None))
    ).all()
    if current_user.is_staff:
        return any(access.can_view_child(current_user, child) for _, child in rows)
    tagged = list({child.id: child for _, child in rows}.values())
    for event, child in rows:
        if event.visibility != "parents" or not access.can_view_child(current_user, child):
            continue
        if photos.visible_to_family_of(child, tagged):
            return True
    return False


def _serve(media_id: str, thumb: bool):
    media = db.session.get(Media, media_id)
    if media is None or not may_see(media):
        abort(404)
    path = uploads.path_of(media.thumb_name if thumb else media.stored_name)
    try:
        response = send_file(path, mimetype=media.content_type, conditional=True)
    except FileNotFoundError:
        abort(404)
    response.headers["Cache-Control"] = "private, max-age=300"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Disposition"] = "inline"
    return response


@bp.get("/<media_id>")
@login_required
def show(media_id: str):
    return _serve(media_id, thumb=False)


@bp.get("/<media_id>/thumb")
@login_required
def thumb(media_id: str):
    return _serve(media_id, thumb=True)
