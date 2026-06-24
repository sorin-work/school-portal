"""School settings stored in the settings table, with defaults in code."""

from flask import current_app, g, has_request_context
from sqlalchemy import select

from .extensions import db
from .models import Setting

DEFAULTS = {
    "school_name": None,  # falls back to SCHOOL_NAME from the environment
    "summary_enabled": "true",
    "summary_time": "17:30",
    "retention_days": "1095",
    "idle_timeout_minutes": "60",
}


def _all() -> dict[str, str]:
    if has_request_context() and "settings" in g:
        return g.settings
    values = {row.key: row.value for row in db.session.scalars(select(Setting))}
    if has_request_context():
        g.settings = values
    return values


def get(key: str) -> str:
    value = _all().get(key)
    if value is None:
        value = DEFAULTS[key]
    if value is None and key == "school_name":
        value = current_app.config["SCHOOL_NAME"]
    return value


def get_int(key: str) -> int:
    return int(get(key))


def get_bool(key: str) -> bool:
    return get(key) == "true"


def put(key: str, value) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    if isinstance(value, bool):
        value = "true" if value else "false"
    row = db.session.get(Setting, key)
    if row is None:
        db.session.add(Setting(key=key, value=str(value)))
    else:
        row.value = str(value)
    if has_request_context():
        g.pop("settings", None)
