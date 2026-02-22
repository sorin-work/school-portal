from datetime import time, timedelta

from school_portal import timeutil
from school_portal.extensions import db
from school_portal.models import Event

from ..conftest import login


def add_event(child, kind="activity", visibility="parents", when=None, **fields):
    event = Event(
        child_id=child.id,
        room_id=child.room_id,
        kind=kind,
        occurred_at=when or timeutil.now() - timedelta(minutes=5),
        visibility=visibility,
        details=fields.pop("details", {"title": f"{kind} for {child.first_name}"}),
        **fields,
    )
    db.session.add(event)
    db.session.commit()
    return event


def test_parent_sees_their_childs_day(client, school):
    add_event(school.ava, details={"title": "Painting with leaves"})
    login(client, school.sam)
    page = client.get(f"/children/{school.ava.id}/diary")
    assert page.status_code == 200
    assert b"Painting with leaves" in page.data


def test_parents_do_not_see_staff_only_events(client, school):
    add_event(school.ava, kind="note", visibility="staff", note="Watch the cough", details={})
    add_event(school.ava, details={"title": "Water play"})
    login(client, school.sam)
    page = client.get(f"/children/{school.ava.id}/diary").data
    assert b"Water play" in page
    assert b"Watch the cough" not in page
    client.post("/logout")
    login(client, school.amy)
    page = client.get(f"/children/{school.ava.id}/diary").data
    assert b"Watch the cough" in page
    assert b"Staff only" in page


def test_removed_events_are_gone_for_everyone(client, school):
    add_event(school.ava, details={"title": "Mistake"}, deleted_at=timeutil.now())
    login(client, school.amy)
    assert b"Mistake" not in client.get(f"/children/{school.ava.id}/diary").data


def test_another_day(client, school):
    yesterday = timeutil.today() - timedelta(days=1)
    add_event(
        school.ava, details={"title": "Walk to the park"}, when=timeutil.at(yesterday, time(10, 0))
    )
    login(client, school.sam)
    assert b"Walk to the park" not in client.get(f"/children/{school.ava.id}/diary").data
    page = client.get(f"/children/{school.ava.id}/diary?day={yesterday.isoformat()}")
    assert b"Walk to the park" in page.data
