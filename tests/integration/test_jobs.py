from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from school_portal import jobs, timeutil
from school_portal.extensions import db
from school_portal.models import Job


def all_jobs():
    return list(db.session.scalars(select(Job).order_by(Job.id)))


def test_enqueue_and_run(app):
    seen = []
    jobs.HANDLERS["test.ok"] = seen.append
    jobs.enqueue("test.ok", {"n": 1})
    db.session.commit()
    assert jobs.run_due() == 1
    (job,) = all_jobs()
    assert job.status == "done" and seen == [{"n": 1}]


def test_unique_keys_queue_once(app):
    jobs.enqueue("test.ok", unique_key="once")
    jobs.enqueue("test.ok", unique_key="once")
    db.session.commit()
    assert len(all_jobs()) == 1


def test_failures_are_retried_later_then_given_up(app):
    def boom(payload):
        raise RuntimeError("smtp is down")

    jobs.HANDLERS["test.boom"] = boom
    jobs.enqueue("test.boom")
    db.session.commit()
    jobs.run_due()
    (job,) = all_jobs()
    assert job.status == "queued" and job.attempts == 1
    assert "smtp is down" in job.last_error
    assert job.run_at > timeutil.now()
    for _ in range(10):
        job.run_at = timeutil.now() - timedelta(seconds=1)
        db.session.commit()
        jobs.run_due()
    db.session.refresh(job)
    assert job.status == "failed" and job.attempts == job.max_attempts


def test_future_jobs_wait(app):
    jobs.enqueue("test.ok", run_at=timeutil.now() + timedelta(hours=1))
    db.session.commit()
    assert jobs.run_due() == 0


def test_unknown_kinds_fail_instead_of_vanishing(app):
    jobs.enqueue("nobody.handles.this")
    db.session.commit()
    jobs.run_due()
    assert "no handler" in all_jobs()[0].last_error


def test_housekeeping_is_scheduled_once_a_day(app):
    early = datetime(2026, 3, 3, 1, 0, tzinfo=UTC)
    later = datetime(2026, 3, 3, 9, 0, tzinfo=UTC)
    jobs.schedule(early)
    assert [j.kind for j in all_jobs()] == []
    jobs.schedule(later)
    jobs.schedule(later + timedelta(hours=1))
    assert [j.kind for j in all_jobs() if j.kind == "housekeeping"] == ["housekeeping"]
