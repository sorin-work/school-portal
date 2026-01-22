from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from sqlalchemy import func, or_, select
from wtforms import BooleanField, DateField, EmailField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from ..decorators import admin_required
from ..extensions import db
from ..models import ACCESS_CHOICES, Child, Guardian, Role, Room, User

bp = Blueprint("admin_children", __name__, url_prefix="/admin/children")


class ChildForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=80)])
    preferred_name = StringField("Known as", validators=[Optional(), Length(max=80)])
    date_of_birth = DateField("Date of birth", validators=[DataRequired()])
    start_date = DateField("Start date", validators=[Optional()])
    room_id = SelectField("Room or class", coerce=int)
    key_person_id = SelectField("Key person", coerce=int)
    dietary_needs = TextAreaField("Dietary needs", validators=[Optional(), Length(max=2000)])
    allergies = TextAreaField("Allergies", validators=[Optional(), Length(max=2000)])
    medical_notes = TextAreaField("Medical notes", validators=[Optional(), Length(max=4000)])
    share_medical_with_parents = BooleanField("Show the medical notes to the family")


class GuardianForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    relationship = StringField("Relationship", default="Parent", validators=[Length(max=40)])
    access = SelectField("Access", choices=ACCESS_CHOICES, default="full")


@bp.get("/")
@admin_required
def index():
    query = select(Child).order_by(Child.first_name, Child.last_name)
    room_id = request.args.get("room", type=int)
    if room_id:
        query = query.where(Child.room_id == room_id)
    term = request.args.get("q", "").strip()
    if term:
        like = f"%{term.lower()}%"
        query = query.where(
            or_(
                func.lower(Child.first_name).like(like),
                func.lower(Child.last_name).like(like),
                func.lower(Child.preferred_name).like(like),
            )
        )
    show_left = False
    rooms = list(db.session.scalars(select(Room).order_by(Room.sort_order, Room.name)))
    return render_template(
        "admin/children.html",
        children=list(db.session.scalars(query)),
        rooms=rooms,
        room_id=room_id,
        term=term,
        show_left=show_left,
    )


def _choices(form: ChildForm) -> None:
    rooms = db.session.scalars(select(Room).order_by(Room.sort_order, Room.name))
    form.room_id.choices = [(0, "No room")] + [(r.id, r.name) for r in rooms]
    staff = db.session.scalars(
        select(User).where(User.role.in_([Role.STAFF, Role.ADMIN]), User.active).order_by(User.name)
    )
    form.key_person_id.choices = [(0, "None")] + [(u.id, u.name) for u in staff]


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    form = ChildForm()
    _choices(form)
    if form.validate_on_submit():
        child = Child()
        _apply(form, child)
        db.session.add(child)
        db.session.flush()
        db.session.commit()
        flash(f"{child.display_name} added.", "success")
        return redirect(url_for(".edit", child_id=child.id))
    return render_template("admin/child_form.html", form=form, child=None)


def _apply(form: ChildForm, child: Child) -> list[str]:
    changed = []
    for name in (
        "first_name",
        "last_name",
        "preferred_name",
        "date_of_birth",
        "start_date",
        "dietary_needs",
        "allergies",
        "medical_notes",
        "share_medical_with_parents",
    ):
        value = getattr(form, name).data
        if isinstance(value, str):
            value = value.strip() or None
        if getattr(child, name) != value:
            changed.append(name)
            setattr(child, name, value)
    for name in ("room_id", "key_person_id"):
        value = getattr(form, name).data or None
        if getattr(child, name) != value:
            changed.append(name)
            setattr(child, name, value)
    return changed


@bp.route("/<int:child_id>", methods=["GET", "POST"])
@admin_required
def edit(child_id: int):
    child = db.get_or_404(Child, child_id)
    form = ChildForm(obj=child)
    _choices(form)
    if not form.is_submitted():
        form.room_id.data = child.room_id or 0
        form.key_person_id.data = child.key_person_id or 0
    if form.validate_on_submit():
        changed = _apply(form, child)
        if changed:
            db.session.commit()
            flash("Saved.", "success")
        return redirect(url_for(".edit", child_id=child.id))
    return render_template(
        "admin/child_form.html",
        form=form,
        child=child,
        guardian_form=GuardianForm(prefix="g"),
    )


@bp.post("/<int:child_id>/guardians")
@admin_required
def add_guardian(child_id: int):
    child = db.get_or_404(Child, child_id)
    form = GuardianForm(prefix="g")
    if not form.validate_on_submit():
        flash("Check the guardian's details: " + _first_error(form), "error")
        return redirect(url_for(".edit", child_id=child.id) + "#guardians")
    email = form.email.data.strip().lower()
    user = db.session.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        flash("There is no account with that address. Add it under Users first.", "error")
        return redirect(url_for(".edit", child_id=child.id) + "#guardians")
    elif user.role != Role.PARENT:
        flash("That address belongs to a staff account. Use a separate parent account.", "error")
        return redirect(url_for(".edit", child_id=child.id) + "#guardians")
    if any(g.user_id == user.id for g in child.guardians):
        flash(f"{user.name} is already linked to {child.display_name}.", "error")
        return redirect(url_for(".edit", child_id=child.id) + "#guardians")
    link = Guardian(
        child=child,
        user_id=user.id,
        relationship_label=form.relationship.data.strip() or "Parent",
        access=form.access.data,
    )
    db.session.add(link)
    db.session.flush()
    db.session.commit()
    flash(f"{user.name} linked to {child.display_name}.", "success")
    return redirect(url_for(".edit", child_id=child.id) + "#guardians")


def _first_error(form) -> str:
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "invalid"


@bp.post("/<int:child_id>/guardians/<int:guardian_id>/remove")
@admin_required
def remove_guardian(child_id: int, guardian_id: int):
    link = db.session.get(Guardian, guardian_id)
    if link is None or link.child_id != child_id:
        abort(404)
    db.session.delete(link)
    db.session.commit()
    flash("Guardian removed from this child.", "success")
    return redirect(url_for(".edit", child_id=child_id) + "#guardians")
