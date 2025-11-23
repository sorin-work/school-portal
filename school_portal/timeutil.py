"""Times are stored in UTC and shown in the school's time zone.

A "day" in the portal is a calendar day where the school is, so the bounds of
a day are worked out in that zone and converted to UTC for queries.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context


def school_tz() -> ZoneInfo:
    name = "Europe/London"
    if has_app_context():
        name = current_app.config.get("SCHOOL_TIMEZONE", name)
    return ZoneInfo(name)


def now() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    return now().astimezone(school_tz())


def today() -> date:
    return now_local().date()


def local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(school_tz())


def at(day: date, clock: time) -> datetime:
    """The UTC instant of a wall-clock time on a school day."""
    return datetime.combine(day, clock, tzinfo=school_tz()).astimezone(UTC)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of a school day, in UTC."""
    return at(day, time(0, 0)), at(day + timedelta(days=1), time(0, 0))


def parse_day(value: str | None, default: date | None = None) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return default or today()


def parse_clock(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def fmt_time(value: datetime | None) -> str:
    if value is None:
        return ""
    return local(value).strftime("%H:%M")


def fmt_date(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = local(value).date()
    return f"{value.day} {value.strftime('%b %Y')}"


def fmt_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return f"{fmt_date(value)}, {fmt_time(value)}"


def fmt_day(value: date) -> str:
    """'Today', 'Yesterday' or 'Tuesday 4 March'."""
    current = today()
    if value == current:
        return "Today"
    if value == current - timedelta(days=1):
        return "Yesterday"
    return f"{value.strftime('%A')} {value.day} {value.strftime('%B')}"


def fmt_isoday(value: datetime) -> str:
    return local(value).date().isoformat()
