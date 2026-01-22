from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func, select
from wtforms import BooleanField, EmailField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, Optional

from ..decorators import admin_required
from ..extensions import db
from ..models import Guardian, Role, User

bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

ROLE_CHOICES = [
    (Role.PARENT.value, "Parent or carer"),
    (Role.STAFF.value, "Staff"),
    (Role.ADMIN.value, "Administrator"),
]


class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    role = SelectField("Role", choices=ROLE_CHOICES)
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    active = BooleanField("Can sign in", default=True)
    password = PasswordField(
        "Password",
        validators=[Optional(), Length(min=10, message="Use at least 10 characters.")],
    )


@bp.get("/")
@admin_required
def index():
    role = request.args.get("role", "")
    query = select(User).order_by(User.name)
    if role in {r.value for r in Role}:
        query = query.where(User.role == role)
    return render_template(
        "admin/users.html", users=list(db.session.scalars(query)), role=role, roles=ROLE_CHOICES
    )


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    form = UserForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if _email_taken(email):
            form.email.errors.append("Another account uses that address.")
        else:
            user = User(
                name=form.name.data.strip(),
                email=email,
                role=form.role.data,
                phone=form.phone.data or None,
                active=form.active.data,
            )
            if form.password.data:
                user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            db.session.commit()
            flash(f"Account for {user.name} created.", "success")
            return redirect(url_for(".edit", user_id=user.id))
    return render_template("admin/user_form.html", form=form, user=None)


def _email_taken(email: str, except_id: int | None = None) -> bool:
    query = select(User.id).where(func.lower(User.email) == email)
    if except_id is not None:
        query = query.where(User.id != except_id)
    return db.session.scalar(query) is not None


@bp.route("/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit(user_id: int):
    user = db.get_or_404(User, user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if _email_taken(email, user.id):
            form.email.errors.append("Another account uses that address.")
        elif user.id == current_user.id and (form.role.data != "admin" or not form.active.data):
            form.role.errors.append("You cannot take away your own administrator access.")
        else:
            user.name = form.name.data.strip()
            user.email = email
            user.role = form.role.data
            user.phone = form.phone.data or None
            user.active = form.active.data
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            flash("Saved.", "success")
            return redirect(url_for(".edit", user_id=user.id))
    links = list(db.session.scalars(select(Guardian).where(Guardian.user_id == user.id)))
    return render_template("admin/user_form.html", form=form, user=user, links=links)
