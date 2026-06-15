"""A small job queue in the jobs table, and the worker that runs it.

There is no broker: the web process inserts a row and the worker polls for
due rows with FOR UPDATE SKIP LOCKED. A failed job is tried again later with
a growing delay, up to max_attempts, then left as "failed" for an
administrator to look at.
"""

import logging
import time
import traceback
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from . import timeutil
from .extensions import db
from .models import Job

log = logging.getLogger(__name__)

HANDLERS: dict[str, Callable[[dict], None]] = {}


def handler(kind: str):
    def register(fn):
        HANDLERS[kind] = fn
        return fn

    return register


def load_handlers() -> None:
    """Import the modules that register handlers."""
    from . import mail  # noqa: F401


def enqueue(kind: str, payload: dict | None = None, *, run_at=None, unique_key=None) -> None:
    """Add a job to the current transaction. A repeated unique_key is ignored."""
    values = {
        "kind": kind,
        "payload": payload or {},
        "run_at": run_at or timeutil.now(),
        "unique_key": unique_key,
        "status": "queued",
        "attempts": 0,
        "max_attempts": 5,
    }
    statement = insert(Job).values(**values)
    if unique_key is not None:
        statement = statement.on_conflict_do_nothing(index_elements=["unique_key"])
    db.session.execute(statement)


def backoff(attempts: int) -> timedelta:
    return timedelta(minutes=min(2**attempts, 120))


def run_due(limit: int = 20) -> int:
    """Run up to `limit` due jobs, one transaction each. Returns how many ran."""
    load_handlers()
    done = 0
    for _ in range(limit):
        job = db.session.scalar(
            select(Job)
            .where(Job.status == "queued", Job.run_at <= timeutil.now())
            .order_by(Job.run_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            break
        job.status = "running"
        job.locked_at = timeutil.now()
        job.attempts += 1
        fn = HANDLERS.get(job.kind)
        try:
            if fn is None:
                raise LookupError(f"no handler for job kind {job.kind!r}")
            fn(dict(job.payload))
        except Exception:
            db.session.rollback()
            job = db.session.get(Job, job.id)
            job.attempts += 1
            job.last_error = traceback.format_exc(limit=5)[-4000:]
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                job.finished_at = timeutil.now()
            else:
                job.status = "queued"
                job.run_at = timeutil.now() + backoff(job.attempts)
            log.exception("job %s (%s) failed", job.id, job.kind)
        else:
            job.status = "done"
            job.finished_at = timeutil.now()
            job.last_error = None
        db.session.commit()
        done += 1
    return done


def schedule(now=None) -> None:
    """Queue the recurring jobs that are due. Safe to call often."""
    now = now or timeutil.now()
    local = timeutil.local(now)
    day = local.date().isoformat()
    log.debug("scheduling for %s", day)
    # Housekeeping runs once a day, early in the morning.
    if local.hour >= 2:
        enqueue("housekeeping", {"day": day}, unique_key=f"housekeeping:{day}")
    db.session.commit()


@handler("housekeeping")
def housekeeping(payload: dict) -> None:
    cutoff = timeutil.now() - timedelta(days=30)
    db.session.execute(Job.__table__.delete().where(Job.status == "done", Job.finished_at < cutoff))


def work_forever(poll_seconds: float = 5.0) -> None:  # pragma: no cover - runs in the worker
    log.info("worker started")
    while True:
        try:
            schedule()
            ran = run_due()
        except Exception:
            db.session.rollback()
            log.exception("worker loop error")
            ran = 0
        if not ran:
            time.sleep(poll_seconds)
