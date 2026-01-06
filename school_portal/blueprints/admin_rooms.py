from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import IntegerField, SelectField, SelectMultipleField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from ..decorators import admin_required
from ..extensions import db
from ..models import Role, Room, RoomStaff, User

bp = Blueprint("admin_rooms", __name__, url_prefix="/admin/rooms")


class RoomForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)])
    kind = SelectField(
        "Kind",
        choices=[("nursery", "Nursery room (naps and nappies)"), ("class", "School class")],
    )
    age_range = StringField("Ages", validators=[Optional(), Length(max=40)])
    capacity = IntegerField("Places", validators=[Optional(), NumberRange(min=1, max=200)])
    sort_order = IntegerField("Order in lists", default=0, validators=[Optional()])
    staff = SelectMultipleField("Staff working here", coerce=int)
    leads = SelectMultipleField("Room leads", coerce=int)


def _staff_choices():
    users = db.session.scalars(
        select(User).where(User.role.in_([Role.STAFF, Role.ADMIN]), User.active).order_by(User.name)
    )
    return [(u.id, u.name) for u in users]


@bp.get("/")
@admin_required
def index():
    rooms = db.session.scalars(select(Room).order_by(Room.sort_order, Room.name))
    return render_template("admin/rooms.html", rooms=list(rooms))


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    return _edit(Room())


@bp.route("/<int:room_id>", methods=["GET", "POST"])
@admin_required
def edit(room_id: int):
    room = db.get_or_404(Room, room_id)
    return _edit(room)


def _edit(room: Room):
    form = RoomForm(obj=room)
    choices = _staff_choices()
    form.staff.choices = choices
    form.leads.choices = choices
    if not form.is_submitted() and room.id:
        form.staff.data = [s.user_id for s in room.staff]
        form.leads.data = [s.user_id for s in room.staff if s.is_lead]
    if form.validate_on_submit():
        duplicate = db.session.scalar(
            select(Room).where(Room.name == form.name.data.strip(), Room.id != room.id)
        )
        if duplicate is not None:
            form.name.errors.append("Another room has that name.")
        else:
            room.name = form.name.data.strip()
            room.kind = form.kind.data
            room.age_range = form.age_range.data or None
            room.capacity = form.capacity.data
            room.sort_order = form.sort_order.data or 0
            if room.id is None:
                db.session.add(room)
                db.session.flush()
            wanted = set(form.staff.data) | set(form.leads.data)
            leads = set(form.leads.data)
            room.staff = [RoomStaff(user_id=uid, is_lead=uid in leads) for uid in sorted(wanted)]
            db.session.commit()
            flash(f"{room.name} saved.", "success")
            return redirect(url_for(".index"))
    return render_template("admin/room_form.html", form=form, room=room)
