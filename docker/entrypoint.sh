#!/bin/sh
# Bring the schema up to date, seed the demo school when asked, then run the
# command (gunicorn for the app, "flask worker" for the worker).
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

if [ "${SEED_DEMO:-false}" = "true" ]; then
  flask --app school_portal seed-demo
fi

exec "$@"
