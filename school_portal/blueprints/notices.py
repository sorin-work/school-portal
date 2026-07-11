from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import or_, select
from wtforms import BooleanField, DateField, SelectMultipleField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from .. import access, timeutil
from ..extensions import db
from ..models import Child, Guardian, Notice, Room, User
from ..models.notice import notice_rooms
from ..notify import notify

bp = Blueprint("notices", __name__, url_prefix="/notices")


class NoticeForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    body = TextAreaField("Notice", validators=[DataRequired(), Length(max=10000)])
    rooms = SelectMultipleField("For the families of", coerce=int)
    expires_on = DateField("Show until", validators=[Optional()])
    pinned = BooleanField("Keep at the top")


def family_room_ids(user: User) -> set[int]:
    return {
        c.room_id for c in db.session.scalars(access.children_query(user)) if c.room_id is not None
    }


def notices_for(user: User) -> list[Notice]:
    query = select(Notice).order_by(Notice.pinned.desc(), Notice.published_at.desc())
    query = query.where(or_(Notice.expires_on.is_(None), Notice.expires_on >= timeutil.today()))
    if not user.is_staff:
        rooms = family_room_ids(user)
        everyone = (
            ~select(notice_rooms.c.notice_id).where(notice_rooms.c.notice_id == Notice.id).exists()
        )
        mine = (
            select(notice_rooms.c.notice_id)
            .where(notice_rooms.c.notice_id == Notice.id, notice_rooms.c.room_id.in_(rooms))
            .exists()
        )
        query = query.where(or_(everyone, mine))
    return list(db.session.scalars(query.limit(100)))


def may_post(user: User) -> bool:
    return user.is_admin or bool(access.lead_room_ids(user))


@bp.get("/")
@login_required
def index():
    return render_template(
        "notices/index.html", notices=notices_for(current_user), may_post=may_post(current_user)
    )


@bp.get("/<int:notice_id>")
@login_required
def show(notice_id: int):
    notice = next((n for n in notices_for(current_user) if n.id == notice_id), None)
    if notice is None:
        abort(404)
    return render_template("notices/show.html", notice=notice, may_edit=_may_edit(notice))


def _may_edit(notice: Notice) -> bool:
    if current_user.is_admin:
        return True
    if not current_user.is_staff or notice.author_id != current_user.id:
        return False
    return bool(notice.rooms) and {r.id for r in notice.rooms} <= access.lead_room_ids(current_user)


def _room_choices() -> list[tuple[int, str]]:
    if current_user.is_admin:
        rooms = db.session.scalars(select(Room).order_by(Room.sort_order))
    else:
        ids = access.lead_room_ids(current_user)
        rooms = db.session.scalars(select(Room).where(Room.id.in_(ids)).order_by(Room.sort_order))
    return [(r.id, r.name) for r in rooms]


def _families(notice: Notice) -> list[User]:
    query = (
        select(User)
        .join(Guardian, Guardian.user_id == User.id)
        .join(Child, Child.id == Guardian.child_id)
        .where(Guardian.access.in_(["full", "read_only"]), User.active)
        .distinct()
    )
    if notice.rooms:
        query = query.where(Child.room_id.in_([r.id for r in notice.rooms]))
    return list(db.session.scalars(query))


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if not may_post(current_user):
        abort(403)
    return _form(Notice(), new=True)


@bp.route("/<int:notice_id>/edit", methods=["GET", "POST"])
@login_required
def edit(notice_id: int):
    notice = db.get_or_404(Notice, notice_id)
    if not _may_edit(notice):
        abort(403)
    return _form(notice, new=False)


def _form(notice: Notice, *, new: bool):
    form = NoticeForm(obj=notice)
    form.rooms.choices = _room_choices()
    if not form.is_submitted():
        form.rooms.data = [r.id for r in notice.rooms]
    if form.validate_on_submit():
        allowed = {value for value, _ in form.rooms.choices}
        chosen = [rid for rid in form.rooms.data if rid in allowed]
        if not chosen and not current_user.is_admin:
            form.rooms.errors.append("Choose your room.")
        else:
            notice.title = form.title.data.strip()
            notice.body = form.body.data.strip()
            notice.expires_on = form.expires_on.data
            notice.pinned = form.pinned.data
            notice.rooms = list(db.session.scalars(select(Room).where(Room.id.in_(chosen))))
            if new:
                notice.author_id = current_user.id
                db.session.add(notice)
                db.session.flush()
                notify(
                    _families(notice),
                    "notice",
                    f"Notice: {notice.title}",
                    url_for("notices.show", notice_id=notice.id),
                )
            db.session.commit()
            flash("Notice published." if new else "Notice saved.", "success")
            return redirect(url_for(".show", notice_id=notice.id))
    return render_template("notices/form.html", form=form, notice=notice, new=new)


@bp.post("/<int:notice_id>/delete")
@login_required
def delete(notice_id: int):
    notice = db.get_or_404(Notice, notice_id)
    if not _may_edit(notice):
        abort(403)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice removed.", "success")
    return redirect(url_for(".index"))
