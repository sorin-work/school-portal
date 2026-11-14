# Operations

## Running it

The image runs `alembic upgrade head` on start (turn it off with
`RUN_MIGRATIONS=false`), seeds the demo school if `SEED_DEMO=true` and the
database has no users, then starts gunicorn on port 8000. The worker is the
same image with `flask --app school_portal worker` as its command; run one,
or more if the queue grows.

Behind a reverse proxy with HTTPS, set `SESSION_COOKIE_SECURE=true`,
`APP_ENV=production`, a long random `SECRET_KEY` and `BASE_URL` to the public
address. The app uses `request.remote_addr` for the rate limit and the audit
log, so the proxy should pass the client address (for example with
gunicorn's `--forwarded-allow-ips`).

## Health

`GET /healthz` answers `{"status": "ok", "database": "ok"}` or 503. The
compose file uses it for the app's health check.

## Background jobs

Settings shows how many jobs are queued, running, done and failed, and the
last error of the failed ones. To run the queue by hand:

```sh
docker compose exec app flask --app school_portal run-jobs
```

Done jobs older than 30 days are removed by the nightly housekeeping job,
which also prunes sign-in attempts older than a week and deletes the records
of children past their retention date. `flask --app school_portal
purge-leavers` does the last part on its own.

## Email

Development mail goes to Mailpit (UI on http://127.0.0.1:8033). For real
mail, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_TLS=true` and `MAIL_FROM`. A mail server that is down only delays
mail: the job is retried for about half an hour, then marked failed.

## Backups

The app does not back itself up. Back up the database (`pg_dump`) and the
`uploads` volume together; a dump without the photos, or the other way
round, restores into broken links.

## Upgrades

Pull, rebuild, start. Migrations run on start. Each migration has a
downgrade, but the safe way back is the backup taken before the upgrade.

## Accounts

- First administrator on an empty database:
  `flask --app school_portal create-admin`.
- Everyone else is invited from Users or from a child's page; the
  invitation link is valid for seven days and can be sent again.
