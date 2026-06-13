from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from sqlalchemy import func, select
from wtforms import EmailField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from .. import timeutil, tokens
from ..extensions import db
from ..mail import queue_email
from ..models import User

bp = Blueprint("auth", __name__)

DEMO_LOGINS = [
    ("demo@example.com", "Administrator"),
    ("amira.lead@example.com", "Staff, room lead in Saplings"),
    ("tom.staff@example.com", "Staff in Acorns"),
    ("parent@example.com", "Parent of two children"),
    ("parent2@example.com", "Parent of one child"),
    ("restricted@example.com", "Guardian with no access (court order)"),
]


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class ForgotForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])


class SetPasswordForm(FlaskForm):
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=10, message="Use at least 10 characters.")],
    )
    confirm = PasswordField(
        "Repeat it", validators=[DataRequired(), EqualTo("password", "The passwords differ.")]
    )


def normalise_email(value: str) -> str:
    return value.strip().lower()


def find_user(email: str) -> User | None:
    return db.session.scalar(select(User).where(func.lower(User.email) == normalise_email(email)))


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
    if current_app.config.get("SHOW_DEMO_LOGINS"):
        return DEMO_LOGINS
    return []


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You are signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = find_user(form.email.data)
        # The same answer whether or not the address has an account.
        if user is not None and user.active and tokens.may_send_reset(user):
            token = tokens.issue(user, "reset")
            queue_email(
                user.email,
                "Reset your password",
                "email/reset.txt",
                user=user,
                link=current_app.config["BASE_URL"] + url_for("auth.reset", token=token),
            )
            db.session.commit()
        flash("If that address has an account, a reset link is on its way.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot.html", form=form)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token: str):
    record = tokens.find(token)
    if record is None:
        flash("That link has expired or was already used. Ask for a new one.", "error")
        return redirect(url_for("auth.forgot"))
    form = SetPasswordForm()
    if form.validate_on_submit():
        user = record.user
        user.set_password(form.password.data)
        record.used_at = timeutil.now()
        db.session.commit()
        flash("Your password is set. Sign in with it now.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset.html", form=form, invite=record.purpose == "invite")
