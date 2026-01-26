from datetime import UTC, datetime, timedelta

from school_portal.models import Event


def event(kind, **details):
    return Event(kind=kind, details=details, occurred_at=datetime(2026, 3, 2, 12, tzinfo=UTC))


def test_meal_summary():
    assert event("meal", meal="lunch", amount="most", menu="Soup").summary() == "Lunch (Soup): most"


def test_nap_summary():
    nap = event("nap")
    assert nap.summary() == "Asleep"
    nap.ended_at = nap.occurred_at + timedelta(minutes=40)
    assert nap.summary() == "Slept for 40 minutes"


def test_nappy_toilet_and_mood():
    assert event("nappy", type="dirty").summary() == "Nappy: dirty"
    assert event("toilet", result="tried").summary() == "Toilet: tried"
    assert event("mood", mood="tired").summary() == "Feeling tired"


def test_activity_uses_its_title():
    assert event("activity", title="Forest school").summary() == "Forest school"
    assert event("activity").label == "Activity"
