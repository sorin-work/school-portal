from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from ..extensions import db
from ..models import Guardian

bp = Blueprint("account", __name__, url_prefix="/account")


class DetailsForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])


class PasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=10, message="Use at least 10 characters.")],
    )
    confirm = PasswordField(
        "Repeat it", validators=[DataRequired(), EqualTo("password", "The passwords differ.")]
    )


def _links():
    return list(db.session.scalars(select(Guardian).where(Guardian.user_id == current_user.id)))


@bp.route("/", methods=["GET", "POST"])
@login_required
def edit():
    details = DetailsForm(prefix="d", obj=current_user)
    password = PasswordForm(prefix="p")
    if request.method == "POST" and request.form.get("form") == "details" and details.validate():
        current_user.name = details.name.data.strip()
        current_user.phone = details.phone.data or None
        db.session.commit()
        flash("Saved.", "success")
        return redirect(url_for(".edit"))
    if request.method == "POST" and request.form.get("form") == "password" and password.validate():
        if not current_user.check_password(password.current.data):
            password.current.errors.append("That is not your current password.")
        else:
            current_user.set_password(password.password.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for(".edit"))
    links = [link for link in _links() if link.can_view] if current_user.is_parent else []
    return render_template("account/edit.html", details=details, password=password, links=links)


@bp.post("/summaries")
@login_required
def summaries():
    wanted = {int(v) for v in request.form.getlist("child_ids") if v.isdigit()}
    for link in _links():
        link.receives_summary = link.child_id in wanted
    db.session.commit()
    flash("Email choices saved.", "success")
    return redirect(url_for(".edit"))
