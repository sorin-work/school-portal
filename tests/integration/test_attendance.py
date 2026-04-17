from sqlalchemy import select

from school_portal import timeutil
from school_portal.extensions import db
from school_portal.models import Attendance

from ..conftest import login


def rows(child):
    return list(db.session.scalars(select(Attendance).where(Attendance.child_id == child.id)))


def test_check_in_and_out_with_a_guardian(client, school):
    login(client, school.amy)
    base = f"/rooms/{school.saplings.id}/children/{school.ava.id}"
    response = client.post(f"{base}/check-in")
    assert b"In since" in response.data
    form = client.get(f"{base}/check-out")
    assert b"Sam Reid" in form.data
    response = client.post(f"{base}/check-out", data={"collector": f"g:{school.sam.id}"})
    assert b"Went home" in response.data
    (row,) = rows(school.ava)
    assert row.day == timeutil.today()
    assert row.collected_by == "Sam Reid"
    assert row.checked_out_by_id == school.amy.id


def test_check_out_needs_someone(client, school):
    login(client, school.amy)
    base = f"/rooms/{school.saplings.id}/children/{school.ava.id}"
    client.post(f"{base}/check-in")
    response = client.post(f"{base}/check-out", data={"collector": "other", "other": ""})
    assert b"Say who collected" in response.data
    response = client.post(f"{base}/check-out", data={"collector": "other", "other": "Aunt Bea"})
    assert rows(school.ava)[0].collected_by == "Aunt Bea"


def test_register_lists_the_room(client, school):
    login(client, school.amy)
    page = client.get(f"/rooms/{school.saplings.id}/register")
    assert b"Ava Reid" in page.data and b"Leon Kowalczyk" in page.data
    assert b"Kit" not in page.data


def test_parents_see_arrival_in_the_diary(client, school):
    login(client, school.amy)
    client.post(f"/rooms/{school.saplings.id}/children/{school.ava.id}/check-in")
    client.post("/logout")
    login(client, school.sam)
    assert b"Arrived" in client.get(f"/children/{school.ava.id}/diary").data
