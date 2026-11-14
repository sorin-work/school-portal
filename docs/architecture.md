# Architecture

One Flask application, one PostgreSQL database and one worker process that
runs from the same code.
Pages are rendered on the server with Jinja. htmx swaps parts of a page
where a full reload would slow staff down: a child's panel in the room view,
the register rows, the message list and the notification count. There is no
single-page app and no JSON API.

## Requests

```
browser -> gunicorn -> Flask app -> blueprint view -> access.py -> SQLAlchemy -> PostgreSQL
```

- `school_portal/__init__.py` builds the app: configuration, extensions
  (SQLAlchemy, Flask-Login, CSRF), blueprints and template filters.
  It also installs the idle session check (`sessions.py`) and the security
  headers (`security_headers.py`).
- Each area has a blueprint in `school_portal/blueprints/`. Views stay thin:
  they load what the user may see through `access.py`, call a helper and
  render a template.
- `access.py` is the one place that decides which children a user may see
  (see [permissions](permissions.md)). Lists start from `children_query()`
  and single records from `child_or_404()`.
- `events.py` creates diary events and reads a child's day; the room view
  and the diary use it, and so does the daily summary.

## Times

Everything is stored as `timestamptz` in UTC. A "day" is a calendar day in
`SCHOOL_TIMEZONE`; `timeutil.day_bounds()` turns a day into a UTC range for
queries, and the template filters show times in the school's zone. A child's
diary for 2 July holds what happened between midnight and midnight in
London, whatever the server's own clock says.

## Files

Photos are stored under `UPLOAD_DIR` in folders named after the first two
characters of a random id. The web server never serves that folder: every
image goes through `media.show` or `media.thumb`, which look up the photo's
events and check the viewer (see `blueprints/media.py`). `uploads.py`
checks, cleans and writes the files.

## Background work

There is no broker. `jobs.enqueue()` adds a row to the `jobs` table in the
same transaction as the change that caused it, so an email is only sent if
the change was saved. The worker (`flask --app school_portal worker`) loops:

1. `jobs.schedule()` queues the recurring jobs that are due. Each has a
   unique key (`summary:2026-03-02`, `housekeeping:2026-03-02`), so running
   it every few seconds, or in two workers, queues each one once.
2. `jobs.run_due()` takes one due row at a time with
   `SELECT ... FOR UPDATE SKIP LOCKED`, runs its handler and marks it done.
   A failure is retried with a growing delay (2, 4, 8 ... minutes, at most two
   hours) and given up after five attempts. Failed jobs show under Settings.

Handlers: `email` (one message), `daily_summary` (writes one `email` job per
family) and `housekeeping` (removes old jobs and sign-in attempts, and
deletes the records of children past their retention date).

## Front end

Tailwind builds `static/dist/app.css` from the templates (`npm run css`).
htmx is vendored in `static/js/htmx.min.js`, and `static/js/app.js` holds
the few behaviours that would otherwise need inline handlers, which the
Content-Security-Policy does not allow: confirm dialogs (`data-confirm`),
"all or none" checkboxes and resetting a form after an htmx post. Every htmx
request carries the CSRF token from the `hx-headers` attribute on `body`.

## Tests

The tests run against a real PostgreSQL. The session fixture builds the
schema with the Alembic migrations, and `test_migrations.py` compares the
result with the models, so a model change without a migration fails CI.
