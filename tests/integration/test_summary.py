from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select

from school_portal import jobs, settings, timeutil
from school_portal.extensions import db
from school_portal.models import Event, Job
from school_portal.summary import build_summaries


def add(child, kind="activity", visibility="parents", title="Water play", day=None):
    day = day or timeutil.today()
    event = Event(
        child_id=child.id,
        room_id=child.room_id,
        kind=kind,
        occurred_at=timeutil.at(day, time(0, 5)),
        details={"title": title},
        visibility=visibility,
    )
    db.session.add(event)
    db.session.commit()
    return event


def test_one_email_per_parent_with_their_children(school):
    add(school.ava, title="Water play")
    add(school.kit, title="Obstacle course")
    summaries = build_summaries(timeutil.today())
    assert set(summaries) == {school.sam.id, school.pat.id}
    ((child, events),) = summaries[school.sam.id]
    assert child.id == school.ava.id and [e.summary() for e in events] == ["Water play"]


def test_nothing_in_the_diary_means_no_email(school):
    assert build_summaries(timeutil.today()) == {}


def test_parents_can_turn_it_off(school):
    add(school.ava)
    school.ava.guardians[0].receives_summary = False
    db.session.commit()
    assert school.sam.id not in build_summaries(timeutil.today())


def test_no_access_guardians_get_nothing(school):
    add(school.ava)
    school.ava.guardians[0].access = "none"
    db.session.commit()
    assert build_summaries(timeutil.today()) == {}


def test_the_job_sends_the_emails(app, school):
    add(school.ava, title="Water play")
    jobs.load_handlers()
    jobs.enqueue("daily_summary", {"day": timeutil.today().isoformat()})
    db.session.commit()
    jobs.run_due()
    jobs.run_due()
    (message,) = app.extensions["outbox"]
    assert message["To"] == school.sam.email
    assert "Water play" in message.get_content()


def test_scheduled_at_the_set_time_on_weekdays(app):
    settings.put("summary_time", "17:30")
    db.session.commit()
    monday = datetime(2026, 3, 2, 17, 0, tzinfo=UTC)  # 17:00 in London
    jobs.schedule(monday)
    assert not db.session.scalars(select(Job).where(Job.kind == "daily_summary")).all()
    jobs.schedule(monday + timedelta(minutes=45))
    jobs.schedule(monday + timedelta(minutes=50))
    assert len(db.session.scalars(select(Job).where(Job.kind == "daily_summary")).all()) == 1
    saturday = datetime(2026, 3, 7, 18, 0, tzinfo=UTC)
    jobs.schedule(saturday)
    assert len(db.session.scalars(select(Job).where(Job.kind == "daily_summary")).all()) == 1
