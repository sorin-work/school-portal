from datetime import UTC, date, datetime, time

from school_portal import timeutil


def test_day_bounds_follow_the_school_time_zone():
    # 1 July is in British Summer Time, so the day starts at 23:00 UTC.
    start, end = timeutil.day_bounds(date(2026, 7, 1))
    assert start == datetime(2026, 6, 30, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 7, 1, 23, 0, tzinfo=UTC)


def test_day_bounds_in_winter():
    start, end = timeutil.day_bounds(date(2026, 1, 15))
    assert start == datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 16, 0, 0, tzinfo=UTC)


def test_at_converts_a_wall_clock_time():
    assert timeutil.at(date(2026, 7, 1), time(9, 30)) == datetime(2026, 7, 1, 8, 30, tzinfo=UTC)


def test_parse_day_falls_back_on_bad_input():
    assert timeutil.parse_day("2026-02-03") == date(2026, 2, 3)
    assert timeutil.parse_day("not a day", date(2026, 1, 1)) == date(2026, 1, 1)


def test_parse_clock():
    assert timeutil.parse_clock("09:15") == time(9, 15)
    assert timeutil.parse_clock("") is None
    assert timeutil.parse_clock("25:99") is None


def test_formatting():
    moment = datetime(2026, 7, 1, 8, 5, tzinfo=UTC)
    assert timeutil.fmt_time(moment) == "09:05"
    assert timeutil.fmt_date(date(2026, 3, 4)) == "4 Mar 2026"
