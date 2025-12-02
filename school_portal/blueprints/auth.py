from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import EmailField, PasswordField
from wtforms.validators import DataRequired, Email

from .. import timeutil
from ..extensions import db
from ..models import User

bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


def normalise_email(value: str) -> str:
    return value.strip().lower()


def find_user(email: str) -> User | None:
    return db.session.scalar(select(User).where(User.email == email.strip()))


def client_ip() -> str:
    return request.remote_addr or "unknown"


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    form = LoginForm()
    if form.validate_on_submit():
        email = normalise_email(form.email.data)
        user = find_user(email)
        if user is None or not user.active or not user.check_password(form.password.data):
            flash("That email and password do not match an account.", "error")
            return render_template("auth/login.html", form=form, demo=_demo()), 401
        user.last_login_at = timeutil.now()
        db.session.commit()
        login_user(user)
        target = request.args.get("next", "")
        # Only follow local paths, never another site.
        if not target.startswith("/") or target.startswith("//"):
            target = url_for("dashboard.home")
        return redirect(target)
    return render_template("auth/login.html", form=form, demo=_demo())


def _demo():
    return []


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You are signed out.", "info")
    return redirect(url_for("auth.login"))
