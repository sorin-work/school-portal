"""The school calendar: trips, closures and events, with replies and trip consent."""

import csv
import io
from datetime import time, timedelta
from itertools import groupby

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import or_, select
from wtforms import (
    BooleanField,
    DateField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, Optional

from .. import access, timeutil
from ..decorators import admin_required, staff_required
from ..extensions import db
from ..models import EVENT_KINDS, Child, Guardian, Room, Rsvp, SchoolEvent, User
from ..models.calendar import school_event_rooms
from ..notify import notify

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


class SchoolEventForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    kind = SelectField("Kind", choices=EVENT_KINDS)
    day = DateField("Date", validators=[DataRequired()])
    all_day = BooleanField("All day")
    start = TimeField("Starts", validators=[Optional()])
    end = TimeField("Ends", validators=[Optional()])
    location = StringField("Where", validators=[Optional(), Length(max=160)])
    description = TextAreaField("Details", validators=[Optional(), Length(max=10000)])
    rooms = SelectMultipleField("For", coerce=int)
    rsvp_required = BooleanField("Ask families whether their child is coming")
    consent_required = BooleanField("Ask for consent (trips)")
    consent_text = TextAreaField(
        "What families consent to", validators=[Optional(), Length(max=4000)]
    )
    respond_by = DateField("Reply by", validators=[Optional()])


def _audience_filter(query, user: User):
    if user.is_staff:
        return query
    from .notices import family_room_ids

    rooms = family_room_ids(user)
    everyone = (
        ~select(school_event_rooms.c.school_event_id)
        .where(school_event_rooms.c.school_event_id == SchoolEvent.id)
        .exists()
    )
    mine = (
        select(school_event_rooms.c.school_event_id)
        .where(
            school_event_rooms.c.school_event_id == SchoolEvent.id,
            school_event_rooms.c.room_id.in_(rooms),
        )
        .exists()
    )
    return query.where(or_(everyone, mine))


def events_for(user: User, *, past: bool = False) -> list[SchoolEvent]:
    cutoff = timeutil.day_bounds(timeutil.today())[0]
    query = select(SchoolEvent)
    if past:
        query = query.where(SchoolEvent.starts_at < cutoff).order_by(SchoolEvent.starts_at.desc())
    else:
        query = query.where(
            or_(SchoolEvent.starts_at >= cutoff, SchoolEvent.ends_at >= cutoff)
        ).order_by(SchoolEvent.starts_at)
    return list(db.session.scalars(_audience_filter(query, user).limit(200)))


def event_or_404(event_id: int) -> SchoolEvent:
    event = db.session.get(SchoolEvent, event_id)
    if event is None:
        abort(404)
    query = _audience_filter(select(SchoolEvent.id).where(SchoolEvent.id == event_id), current_user)
    if db.session.scalar(query) is None:
        abort(404)
    return event


def audience_children(event: SchoolEvent) -> list[Child]:
    query = select(Child).order_by(Child.first_name)
    query = query.where(Child.left_on.is_(None))
    if event.rooms:
        query = query.where(Child.room_id.in_([r.id for r in event.rooms]))
    return list(db.session.scalars(query))


@bp.get("/")
@login_required
def index():
    past = request.args.get("past") == "1"
    events = events_for(current_user, past=past)
    months = [
        (month, list(items))
        for month, items in groupby(
            events, key=lambda e: timeutil.local(e.starts_at).strftime("%B %Y")
        )
    ]
    return render_template("calendar/index.html", months=months, past=past)


@bp.get("/<int:event_id>")
@login_required
def show(event_id: int):
    event = event_or_404(event_id)
    responses = {
        r.child_id: r
        for r in db.session.scalars(select(Rsvp).where(Rsvp.school_event_id == event.id))
    }
    context = {"event": event, "responses": responses, "open": _still_open(event)}
    if current_user.is_staff:
        context["children"] = audience_children(event)
    else:
        in_audience = {c.id for c in audience_children(event)}
        context["mine"] = [
            (child, access.can_act_for_child(current_user, child))
            for child in db.session.scalars(access.children_query(current_user))
            if child.id in in_audience
        ]
    return render_template("calendar/show.html", **context)


def _still_open(event: SchoolEvent) -> bool:
    if event.respond_by is not None:
        return timeutil.today() <= event.respond_by
    return event.starts_at > timeutil.now()


@bp.post("/<int:event_id>/children/<int:child_id>/reply")
@login_required
def reply(event_id: int, child_id: int):
    event = event_or_404(event_id)
    child = access.child_or_404(child_id, act=True)
    if not event.asks_parents or child.id not in {c.id for c in audience_children(event)}:
        abort(404)
    if not _still_open(event):
        flash("Replies for this event have closed. Speak to the office.", "error")
        return redirect(url_for(".show", event_id=event.id))
    attending = request.form.get("attending")
    if attending not in ("yes", "no"):
        flash("Say whether your child is coming.", "error")
        return redirect(url_for(".show", event_id=event.id))
    consent = request.form.get("consent") == "yes"
    signed = (request.form.get("signed_name") or "").strip()[:120]
    if event.consent_required and attending == "yes" and (not consent or not signed):
        flash("To say yes, tick the consent box and type your name.", "error")
        return redirect(url_for(".show", event_id=event.id))
    rsvp = db.session.scalar(
        select(Rsvp).where(Rsvp.school_event_id == event.id, Rsvp.child_id == child.id)
    )
    if rsvp is None:
        rsvp = Rsvp(school_event_id=event.id, child_id=child.id)
        db.session.add(rsvp)
    rsvp.attending = attending == "yes"
    rsvp.consent_given = consent and rsvp.attending
    rsvp.signed_name = signed if rsvp.consent_given else None
    rsvp.note = (request.form.get("note") or "").strip()[:1000] or None
    rsvp.responded_by_id = current_user.id
    rsvp.responded_at = timeutil.now()
    db.session.commit()
    flash(f"Reply for {child.display_name} saved.", "success")
    return redirect(url_for(".show", event_id=event.id))


def _cell(value) -> str:
    text = "" if value is None else str(value)
    # A cell starting with one of these is run as a formula by spreadsheets.
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        text = "'" + text
    return text


@bp.get("/<int:event_id>/replies.csv")
@staff_required
def replies_csv(event_id: int):
    event = event_or_404(event_id)
    responses = {
        r.child_id: r
        for r in db.session.scalars(select(Rsvp).where(Rsvp.school_event_id == event.id))
    }
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Child", "Room", "Reply", "Consent", "Signed by", "Note", "Answered"])
    for child in audience_children(event):
        r = responses.get(child.id)
        writer.writerow(
            [
                _cell(child.display_name),
                _cell(child.room.name if child.room else ""),
                "" if r is None else ("Coming" if r.attending else "Not coming"),
                "" if r is None else ("Yes" if r.consent_given else "No"),
                _cell(r.signed_name if r else ""),
                _cell(r.note if r else ""),
                timeutil.fmt_datetime(r.responded_at) if r else "",
            ]
        )
    filename = f"replies-{event.id}.csv"
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    return _form(SchoolEvent(), new=True)


@bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(event_id: int):
    return _form(db.get_or_404(SchoolEvent, event_id), new=False)


def _form(event: SchoolEvent, *, new: bool):
    form = SchoolEventForm(obj=event)
    form.rooms.choices = [
        (r.id, r.name) for r in db.session.scalars(select(Room).order_by(Room.sort_order))
    ]
    if not form.is_submitted() and not new:
        start = timeutil.local(event.starts_at)
        form.day.data = start.date()
        form.start.data = None if event.all_day else start.time()
        form.end.data = (
            None if event.all_day or event.ends_at is None else timeutil.local(event.ends_at).time()
        )
        form.rooms.data = [r.id for r in event.rooms]
    if form.validate_on_submit():
        day = form.day.data
        if form.all_day.data or form.start.data is None:
            starts, ends, all_day = timeutil.at(day, time(0, 0)), None, True
        else:
            starts = timeutil.at(day, form.start.data)
            ends = timeutil.at(day, form.end.data) if form.end.data else None
            all_day = False
        if ends is not None and ends <= starts:
            form.end.errors.append("It has to end after it starts.")
        elif form.consent_required.data and not (form.consent_text.data or "").strip():
            form.consent_text.errors.append("Say what families are consenting to.")
        else:
            event.title = form.title.data.strip()
            event.kind = form.kind.data
            event.starts_at, event.ends_at, event.all_day = starts, ends, all_day
            if all_day:
                event.ends_at = timeutil.at(day + timedelta(days=1), time(0, 0))
            event.location = form.location.data or None
            event.description = form.description.data or None
            event.rsvp_required = form.rsvp_required.data or form.consent_required.data
            event.consent_required = form.consent_required.data
            event.consent_text = form.consent_text.data or None
            event.respond_by = form.respond_by.data
            event.rooms = list(
                db.session.scalars(select(Room).where(Room.id.in_(form.rooms.data or [])))
            )
            if new:
                event.created_by_id = current_user.id
                db.session.add(event)
                db.session.flush()
                notify(
                    _families(event),
                    "calendar",
                    ("Reply needed: " if event.asks_parents else "On the calendar: ") + event.title,
                    url_for("calendar.show", event_id=event.id),
                )
            db.session.commit()
            flash("Saved.", "success")
            return redirect(url_for(".show", event_id=event.id))
    return render_template("calendar/form.html", form=form, event=event, new=new)


def _families(event: SchoolEvent) -> list[User]:
    ids = [c.id for c in audience_children(event)]
    if not ids:
        return []
    return list(
        db.session.scalars(
            select(User)
            .join(Guardian, Guardian.user_id == User.id)
            .where(Guardian.child_id.in_(ids), Guardian.access.in_(["full", "read_only"]))
            .distinct()
        )
    )
