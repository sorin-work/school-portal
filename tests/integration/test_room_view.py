from sqlalchemy import select

from school_portal.extensions import db
from school_portal.models import Event

from ..conftest import login


def events_of(child, kind=None):
    query = select(Event).where(Event.child_id == child.id, Event.deleted_at.is_(None))
    if kind:
        query = query.where(Event.kind == kind)
    return list(db.session.scalars(query.order_by(Event.id)))


def test_room_page_lists_the_children(client, school):
    login(client, school.amy)
    page = client.get(f"/rooms/{school.saplings.id}")
    assert page.status_code == 200
    assert b"Ava R." in page.data and b"Leon K." in page.data
    assert b"Kit" not in page.data


def test_everyone_had_lunch(client, school):
    login(client, school.amy)
    response = client.post(
        f"/rooms/{school.saplings.id}/bulk",
        data={
            "kind": "meal",
            "meal": "lunch",
            "amount": "all",
            "menu": "Fish pie",
            f"amount_{school.leon.id}": "some",
            "child_ids": [str(school.ava.id), str(school.leon.id), str(school.kit.id)],
        },
    )
    assert response.status_code == 302
    (ava_lunch,) = events_of(school.ava, "meal")
    (leon_lunch,) = events_of(school.leon, "meal")
    assert ava_lunch.details == {"meal": "lunch", "amount": "all", "menu": "Fish pie"}
    assert leon_lunch.details["amount"] == "some"
    assert ava_lunch.batch_id == leon_lunch.batch_id
    # Kit is in another room, so the tick is ignored.
    assert events_of(school.kit) == []


def test_bulk_activity_needs_a_title(client, school):
    login(client, school.amy)
    client.post(
        f"/rooms/{school.saplings.id}/bulk",
        data={"kind": "activity", "title": "", "child_ids": [str(school.ava.id)]},
    )
    assert events_of(school.ava) == []


def test_nap_start_and_end(client, school):
    login(client, school.amy)
    url = f"/rooms/{school.saplings.id}/children/{school.ava.id}/log"
    response = client.post(url, data={"kind": "nap", "at": "12:30"})
    assert b"Nap started" in response.data
    assert b"Already asleep" in client.post(url, data={"kind": "nap"}).data
    (nap,) = events_of(school.ava, "nap")
    assert nap.ended_at is None
    response = client.post(f"/rooms/{school.saplings.id}/naps/{nap.id}/end", data={"at": "13:45"})
    assert b"Awake" in response.data
    db.session.refresh(nap)
    assert (nap.ended_at - nap.occurred_at).total_seconds() == 75 * 60
    assert nap.summary() == "Slept for 1h 15m"


def test_a_nap_cannot_end_twice_or_before_it_started(client, school):
    login(client, school.amy)
    client.post(
        f"/rooms/{school.saplings.id}/children/{school.ava.id}/log",
        data={"kind": "nap", "at": "12:30"},
    )
    (nap,) = events_of(school.ava, "nap")
    end = f"/rooms/{school.saplings.id}/naps/{nap.id}/end"
    assert b"after the start" in client.post(end, data={"at": "12:00"}).data
    client.post(end, data={"at": "13:00"})
    assert b"already ended" in client.post(end, data={"at": "14:00"}).data
    db.session.refresh(nap)
    assert nap.ended_at.minute == 0


def test_nappies_only_in_nursery_rooms(client, school):
    school.saplings.kind = "class"
    db.session.commit()
    login(client, school.amy)
    response = client.post(
        f"/rooms/{school.saplings.id}/children/{school.ava.id}/log",
        data={"kind": "nappy", "value": "wet"},
    )
    assert response.status_code == 400


def test_mood_and_staff_only_note(client, school):
    login(client, school.amy)
    url = f"/rooms/{school.saplings.id}/children/{school.ava.id}/log"
    client.post(url, data={"kind": "mood", "value": "happy"})
    client.post(
        url,
        data={"kind": "note", "note": "Talked about her new baby brother", "visibility": "staff"},
    )
    mood, note = events_of(school.ava)
    assert mood.summary() == "Feeling happy"
    assert note.visibility == "staff"


def test_unknown_values_are_refused(client, school):
    login(client, school.amy)
    url = f"/rooms/{school.saplings.id}/children/{school.ava.id}/log"
    assert client.post(url, data={"kind": "mood", "value": "ecstatic"}).status_code == 400
    assert client.post(url, data={"kind": "rocket"}).status_code == 400


def test_an_observation_for_two_children(client, school):
    from school_portal.models import CurriculumArea

    area = CurriculumArea(framework="EYFS", code="EYFS-M", name="Mathematics")
    db.session.add(area)
    db.session.commit()
    login(client, school.amy)
    response = client.post(
        f"/rooms/{school.saplings.id}/observe",
        data={
            "child_ids": [str(school.ava.id), str(school.leon.id)],
            "area_id": str(area.id),
            "note": "Counted the pours together",
            "next_steps": "Counting to ten",
        },
    )
    assert response.status_code == 302
    (ava_obs,) = events_of(school.ava, "observation")
    assert ava_obs.area_id == area.id
    assert len(events_of(school.leon, "observation")) == 1


def test_an_observation_needs_children_and_a_note(client, school):
    login(client, school.amy)
    response = client.post(f"/rooms/{school.saplings.id}/observe", data={"note": ""})
    assert b"Choose the children" in response.data
    assert b"Describe what you saw" in response.data
