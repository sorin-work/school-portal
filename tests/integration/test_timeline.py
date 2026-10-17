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


def test_a_day_starts_at_midnight_school_time(client, school):
    from datetime import date

    # 00:30 on 2 July in London is 23:30 UTC on 1 July.
    day = date(2025, 7, 2)
    add_event(school.ava, details={"title": "Early note"}, when=timeutil.at(day, time(0, 30)))
    login(client, school.sam)
    assert b"Early note" in client.get(f"/children/{school.ava.id}/diary?day=2025-07-02").data
    assert b"Early note" not in client.get(f"/children/{school.ava.id}/diary?day=2025-07-01").data


def test_parent_acknowledges_an_accident(client, school):
    report = add_event(
        school.ava,
        kind="accident",
        details={"what": "Grazed knee", "action_taken": "Plaster"},
        note="Grazed knee",
        needs_ack=True,
    )
    login(client, school.sam)
    assert b"I have read this" in client.get(f"/children/{school.ava.id}/diary").data
    client.post(f"/events/{report.id}/acknowledge")
    db.session.refresh(report)
    assert report.acknowledged_by_id == school.sam.id
    assert b"Acknowledged by Sam Reid" in client.get(f"/children/{school.ava.id}/diary").data


def test_other_parents_cannot_acknowledge(client, school):
    report = add_event(school.ava, kind="accident", details={}, note="Bump", needs_ack=True)
    login(client, school.pat)
    assert client.post(f"/events/{report.id}/acknowledge").status_code == 404
    db.session.refresh(report)
    assert report.acknowledged_at is None


def test_staff_cannot_acknowledge_for_the_family(client, school):
    report = add_event(school.ava, kind="accident", details={}, note="Bump", needs_ack=True)
    login(client, school.amy)
    assert client.post(f"/events/{report.id}/acknowledge").status_code == 403


def test_staff_edit_and_remove_an_event(client, school):
    event = add_event(school.ava, kind="note", details={}, note="Typo")
    login(client, school.amy)
    client.post(f"/events/{event.id}/edit", data={"note": "Fixed", "visibility": "staff"})
    db.session.refresh(event)
    assert (event.note, event.visibility, event.updated_by_id) == ("Fixed", "staff", school.amy.id)
    client.post(f"/events/{event.id}/delete")
    db.session.refresh(event)
    assert event.deleted_at is not None


def test_parents_and_other_rooms_cannot_edit(client, school):
    event = add_event(school.ava, kind="note", details={}, note="Original")
    login(client, school.sam)
    assert client.post(f"/events/{event.id}/edit", data={"note": "x"}).status_code == 404
    client.post("/logout")
    login(client, school.ben)
    assert client.post(f"/events/{event.id}/delete").status_code == 404
    db.session.refresh(event)
    assert event.note == "Original" and event.deleted_at is None
