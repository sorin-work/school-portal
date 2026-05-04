"""The register: who is in, who collected them, and absences reported ahead."""

from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from .. import access, timeutil
from ..decorators import staff_required
from ..events import child_days
from ..extensions import db
from ..models import ABSENCE_REASONS, Absence, Attendance, Child, Collector
from .room_view import child_in_room, room_children, room_or_404

bp = Blueprint("attendance", __name__)


@bp.get("/rooms/<int:room_id>/register")
@staff_required
def register(room_id: int):
    room = room_or_404(room_id)
    children = room_children(room)
    day = timeutil.today()
    days = child_days(children, day)
    return render_template("attendance/register.html", room=room, children=children, days=days)


def _row_response(room, child):
    day = child_days([child], timeutil.today())[child.id]
    return render_template("attendance/_row.html", room=room, child=child, day=day)


@bp.post("/rooms/<int:room_id>/children/<int:child_id>/check-in")
@staff_required
def check_in(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    today = timeutil.today()
    db.session.add(
        Attendance(
            child_id=child.id,
            room_id=room.id,
            day=today,
            checked_in_at=timeutil.now(),
            checked_in_by_id=current_user.id,
        )
    )
    db.session.commit()
    return _row_response(room, child)


def collector_choices(child: Child) -> list[tuple[str, str]]:
    """Guardians who may collect, then the child's active collectors."""
    choices = []
    for link in child.guardians:
        choices.append((f"g:{link.user_id}", f"{link.user.name} ({link.relationship_label})"))
    query = select(Collector).where(Collector.child_id == child.id)
    query = query.where(Collector.active)
    for collector in db.session.scalars(query.order_by(Collector.name)):
        label = collector.name + (
            f" ({collector.relationship_label})" if collector.relationship_label else ""
        )
        choices.append((f"c:{collector.id}", label))
    return choices


@bp.route("/rooms/<int:room_id>/children/<int:child_id>/check-out", methods=["GET", "POST"])
@staff_required
def check_out(room_id: int, child_id: int):
    room = room_or_404(room_id)
    child = child_in_room(room, child_id)
    row = db.session.scalar(
        select(Attendance).where(
            Attendance.child_id == child.id,
            Attendance.day == timeutil.today(),
            Attendance.checked_out_at.is_(None),
        )
    )
    if row is None:
        abort(404)
    choices = collector_choices(child)
    if request.method == "POST":
        picked = request.form.get("collector", "")
        other = (request.form.get("other") or "").strip()[:120]
        labels = dict(choices)
        if picked in labels:
            row.collected_by = labels[picked].split(" (")[0]
            if picked.startswith("c:"):
                row.collector_id = int(picked[2:])
        elif picked == "other" and other:
            row.collected_by = other
            row.note = (request.form.get("note") or "").strip() or None
        else:
            return render_template(
                "attendance/_checkout.html",
                room=room,
                child=child,
                choices=choices,
                collectors=_collectors(child),
                error="Say who collected the child.",
            )
        row.checked_out_at = timeutil.now()
        row.checked_out_by_id = current_user.id
        db.session.commit()
        return _row_response(room, child)
    return render_template(
        "attendance/_checkout.html",
        room=room,
        child=child,
        choices=choices,
        collectors=_collectors(child),
        error=None,
    )


def _collectors(child: Child) -> list:
    return list(
        db.session.scalars(
            select(Collector).where(Collector.child_id == child.id, Collector.active)
        )
    )


class AbsenceForm(FlaskForm):
    start_date = DateField("From", validators=[DataRequired()])
    end_date = DateField("Until", validators=[DataRequired()])
    reason = SelectField("Reason", choices=ABSENCE_REASONS)
    note = TextAreaField(
        "Anything the staff should know", validators=[Optional(), Length(max=1000)]
    )


@bp.route("/children/<int:child_id>/absence", methods=["GET", "POST"])
@login_required
def report_absence(child_id: int):
    child = access.child_or_404(child_id)
    today = timeutil.today()
    form = AbsenceForm(start_date=today, end_date=today)
    if form.validate_on_submit():
        start, end = form.start_date.data, form.end_date.data
        if end < start:
            form.end_date.errors.append("The last day is before the first.")
        elif start < today - timedelta(days=7):
            form.start_date.errors.append("Absences can be reported up to a week back.")
        elif (end - start).days > 60:
            form.end_date.errors.append("Report at most two months at a time.")
        else:
            absence = Absence(
                child_id=child.id,
                start_date=start,
                end_date=end,
                reason=form.reason.data,
                note=(form.note.data or "").strip() or None,
                reported_by_id=current_user.id,
            )
            db.session.add(absence)
            db.session.commit()
            flash("Thank you, the staff have been told.", "success")
            return redirect(url_for(".report_absence", child_id=child.id))
    upcoming = list(
        db.session.scalars(
            select(Absence)
            .where(
                Absence.child_id == child.id,
                Absence.end_date >= today,
                Absence.cancelled_at.is_(None),
            )
            .order_by(Absence.start_date)
        )
    )
    return render_template("attendance/absence.html", child=child, form=form, upcoming=upcoming)


@bp.post("/children/<int:child_id>/absence/<int:absence_id>/cancel")
@login_required
def cancel_absence(child_id: int, absence_id: int):
    child = access.child_or_404(child_id, act=True)
    absence = db.session.get(Absence, absence_id)
    if absence is None or absence.child_id != child.id:
        abort(404)
    absence.cancelled_at = timeutil.now()
    db.session.commit()
    flash("Absence cancelled.", "success")
    return redirect(url_for(".report_absence", child_id=child.id))
