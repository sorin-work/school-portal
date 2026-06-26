from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from sqlalchemy import func, select
from wtforms import BooleanField, IntegerField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp

from .. import settings
from ..decorators import admin_required
from ..extensions import db
from ..models import Job

bp = Blueprint("admin_settings", __name__, url_prefix="/admin/settings")


class SettingsForm(FlaskForm):
    school_name = StringField("School name", validators=[DataRequired(), Length(max=120)])
    summary_enabled = BooleanField("Send the daily summary email")
    summary_time = StringField(
        "Send it at",
        validators=[DataRequired(), Regexp(r"^([01]\d|2[0-3]):[0-5]\d$", message="Use HH:MM.")],
    )
    retention_days = IntegerField(
        "Keep a child's record after they leave for (days)",
        validators=[DataRequired(), NumberRange(min=30, max=36500)],
    )
    idle_timeout_minutes = IntegerField(
        "Sign out after this many idle minutes",
        validators=[DataRequired(), NumberRange(min=5, max=720)],
    )


@bp.route("/", methods=["GET", "POST"])
@admin_required
def edit():
    form = SettingsForm()
    if not form.is_submitted():
        form.school_name.data = settings.get("school_name")
        form.summary_enabled.data = settings.get_bool("summary_enabled")
        form.summary_time.data = settings.get("summary_time")
        form.retention_days.data = settings.get_int("retention_days")
        form.idle_timeout_minutes.data = settings.get_int("idle_timeout_minutes")
    if form.validate_on_submit():
        settings.put("school_name", form.school_name.data.strip())
        settings.put("summary_enabled", form.summary_enabled.data)
        settings.put("summary_time", form.summary_time.data)
        settings.put("retention_days", form.retention_days.data)
        settings.put("idle_timeout_minutes", form.idle_timeout_minutes.data)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for(".edit"))
    jobs = dict(db.session.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    failed = list(
        db.session.scalars(
            select(Job).where(Job.status == "failed").order_by(Job.id.desc()).limit(10)
        )
    )
    return render_template("admin/settings.html", form=form, jobs=jobs, failed=failed)
