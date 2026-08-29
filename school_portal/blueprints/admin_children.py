from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func, or_, select
from wtforms import BooleanField, DateField, EmailField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from .. import audit, timeutil, tokens
from ..decorators import admin_required
from ..extensions import db
from ..mail import queue_email
from ..models import ACCESS_CHOICES, PHOTO_CONSENT_CHOICES, Child, Guardian, Role, Room, User

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
    photo_consent = SelectField("Photo consent", choices=PHOTO_CONSENT_CHOICES, default="none")


class GuardianForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    name = StringField("Name (for a new account)", validators=[Optional(), Length(max=120)])
    relationship = StringField("Relationship", default="Parent", validators=[Length(max=40)])
    access = SelectField("Access", choices=ACCESS_CHOICES, default="full")
    restriction_reason = TextAreaField(
        "Reason for limiting access", validators=[Optional(), Length(max=2000)]
    )


class AccessForm(FlaskForm):
    access = SelectField("Access", choices=ACCESS_CHOICES)
    restriction_reason = TextAreaField(
        "Reason for limiting access", validators=[Optional(), Length(max=2000)]
    )
    receives_summary = BooleanField("Daily summary email")


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
        audit.record("child.created", child)
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
        "photo_consent",
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
            audit.record("child.updated", child, fields=changed)
            db.session.commit()
            flash("Saved.", "success")
        return redirect(url_for(".edit", child_id=child.id))
    audit.record_view(child, "admin")
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
    if form.access.data != "full" and not (form.restriction_reason.data or "").strip():
        flash("Give a reason when a guardian's access is limited.", "error")
        return redirect(url_for(".edit", child_id=child.id) + "#guardians")
    email = form.email.data.strip().lower()
    user = db.session.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        name = (form.name.data or "").strip()
        if not name:
            flash("There is no account for that address yet. Add a name to create one.", "error")
            return redirect(url_for(".edit", child_id=child.id) + "#guardians")
        user = User(email=email, name=name, role=Role.PARENT)
        db.session.add(user)
        db.session.flush()
        _send_invite(user)
        flash(f"Account created and an invitation sent to {email}.", "info")
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
    _record_restriction(link, form.access.data, form.restriction_reason.data)
    db.session.add(link)
    db.session.flush()
    audit.record("guardian.added", child, target=f"user:{user.id}", access=link.access)
    db.session.commit()
    flash(f"{user.name} linked to {child.display_name}.", "success")
    return redirect(url_for(".edit", child_id=child.id) + "#guardians")


def _first_error(form) -> str:
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "invalid"


def _send_invite(user: User) -> None:
    token = tokens.issue(user, "invite")
    queue_email(
        user.email,
        "Your account for the school portal",
        "email/invite.txt",
        user=user,
        link=current_app.config["BASE_URL"] + url_for("auth.reset", token=token),
    )


def _record_restriction(link: Guardian, access: str, reason: str | None) -> bool:
    """Keep who limited a link and why. Returns False when a reason is missing."""
    reason = (reason or "").strip()
    if access == "full":
        link.restriction_reason = None
        link.restricted_by_id = None
        link.restricted_at = None
        return True
    if not reason:
        return False
    if link.access != access or link.restriction_reason != reason or link.restricted_at is None:
        link.restriction_reason = reason
        link.restricted_by_id = current_user.id
        link.restricted_at = timeutil.now()
    return True


@bp.route("/<int:child_id>/guardians/<int:guardian_id>", methods=["GET", "POST"])
@admin_required
def guardian_access(child_id: int, guardian_id: int):
    link = db.session.get(Guardian, guardian_id)
    if link is None or link.child_id != child_id:
        abort(404)
    form = AccessForm(obj=link)
    if form.validate_on_submit():
        before = link.access
        if not _record_restriction(link, form.access.data, form.restriction_reason.data):
            form.restriction_reason.errors.append("Give a reason when access is limited.")
        else:
            link.access = form.access.data
            link.receives_summary = form.receives_summary.data
            audit.record(
                "guardian.access_changed",
                link.child,
                target=f"user:{link.user_id}",
                before=before,
                after=link.access,
            )
            db.session.commit()
            flash("Access saved.", "success")
            return redirect(url_for(".edit", child_id=child_id) + "#guardians")
    return render_template("admin/guardian_access.html", form=form, link=link)


@bp.post("/<int:child_id>/guardians/<int:guardian_id>/remove")
@admin_required
def remove_guardian(child_id: int, guardian_id: int):
    link = db.session.get(Guardian, guardian_id)
    if link is None or link.child_id != child_id:
        abort(404)
    audit.record("guardian.removed", link.child, target=f"user:{link.user_id}")
    db.session.delete(link)
    db.session.commit()
    flash("Guardian removed from this child.", "success")
    return redirect(url_for(".edit", child_id=child_id) + "#guardians")
