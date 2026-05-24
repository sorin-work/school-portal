"""Messages about one child between the family and the staff.

There is no free chat: every conversation belongs to a child, and the people
in it are the child's guardians with full access and the staff who can see
the child.
"""

from flask import Blueprint, abort, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from .. import access
from ..extensions import db
from ..models import Child, Message, MessageRead
from ..notify import notify

bp = Blueprint("messages", __name__)

MAX_LENGTH = 4000


def _last_read(child_id: int) -> int:
    row = db.session.get(MessageRead, (current_user.id, child_id))
    return row.last_read_id if row else 0


def _mark_read(child_id: int, message_id: int) -> None:
    row = db.session.get(MessageRead, (current_user.id, child_id))
    if row is None:
        db.session.add(
            MessageRead(user_id=current_user.id, child_id=child_id, last_read_id=message_id)
        )
    elif message_id > row.last_read_id:
        row.last_read_id = message_id


@bp.get("/messages")
@login_required
def inbox():
    scope = access.children_query(current_user).with_only_columns(Child.id).order_by(None)
    latest = (
        select(Message.child_id, func.max(Message.id).label("last_id"))
        .where(Message.child_id.in_(scope))
        .group_by(Message.child_id)
        .subquery()
    )
    rows = db.session.execute(
        select(Message, Child)
        .join(latest, Message.id == latest.c.last_id)
        .join(Child, Child.id == Message.child_id)
        .order_by(Message.id.desc())
    ).all()
    reads = {
        r.child_id: r.last_read_id
        for r in db.session.scalars(
            select(MessageRead).where(MessageRead.user_id == current_user.id)
        )
    }
    threads = [
        {"child": child, "last": message, "unread": message.id > reads.get(child.id, 0)}
        for message, child in rows
    ]
    children = (
        []
        if current_user.is_staff
        else list(db.session.scalars(access.children_query(current_user)))
    )
    return render_template("messages/inbox.html", threads=threads, children=children)


@bp.get("/children/<int:child_id>/messages")
@login_required
def thread(child_id: int):
    child = access.child_or_404(child_id)
    messages = list(
        db.session.scalars(select(Message).where(Message.child_id == child.id).order_by(Message.id))
    )
    if messages:
        _mark_read(child.id, messages[-1].id)
        db.session.commit()
    return render_template(
        "messages/thread.html",
        child=child,
        messages=messages,
        can_post=access.can_act_for_child(current_user, child),
    )


@bp.post("/children/<int:child_id>/messages")
@login_required
def post(child_id: int):
    child = access.child_or_404(child_id, act=True)
    body = (request.form.get("body") or "").strip()
    if not body or len(body) > MAX_LENGTH:
        abort(400)
    message = Message(child_id=child.id, author_id=current_user.id, body=body)
    db.session.add(message)
    db.session.flush()
    _mark_read(child.id, message.id)
    if current_user.is_staff:
        recipients = [g.user for g in access.acting_guardians(child)]
    else:
        recipients = access.staff_for_child(child) + [
            g.user for g in access.acting_guardians(child) if g.user_id != current_user.id
        ]
    notify(
        [u for u in recipients if u.id != current_user.id],
        "message",
        f"New message about {child.display_name} from {current_user.name}",
        url_for("messages.thread", child_id=child.id),
        child=child,
    )
    db.session.commit()
    messages = list(
        db.session.scalars(select(Message).where(Message.child_id == child.id).order_by(Message.id))
    )
    if request.headers.get("HX-Request"):
        return render_template("messages/_list.html", child=child, messages=messages)
    return render_template("messages/thread.html", child=child, messages=messages, can_post=True)
