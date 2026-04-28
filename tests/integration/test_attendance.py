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


def test_collectors_with_photos(client, school):
    import io

    from ..images import jpeg_with_exif

    login(client, school.amy)
    response = client.post(
        f"/children/{school.ava.id}/collectors",
        data={
            "name": "Jo Marlow",
            "relationship": "Childminder",
            "password_hint": "blue kite",
            "photo": (io.BytesIO(jpeg_with_exif()), "jo.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    page = client.get(f"/children/{school.ava.id}").data
    assert b"Jo Marlow" in page and b"blue kite" in page
    from school_portal.models import Collector

    collector = db.session.scalar(select(Collector))
    assert client.get(f"/media/{collector.photo_id}/thumb").status_code == 200
    base = f"/rooms/{school.saplings.id}/children/{school.ava.id}"
    client.post(f"{base}/check-in")
    client.post(f"{base}/check-out", data={"collector": f"c:{collector.id}"})
    assert rows(school.ava)[0].collector_id == collector.id
    client.post("/logout")
    # The family sees who may collect, but not the password.
    login(client, school.sam)
    page = client.get(f"/children/{school.ava.id}").data
    assert b"Jo Marlow" in page and b"blue kite" not in page
    assert client.get(f"/media/{collector.photo_id}/thumb").status_code == 200
    client.post("/logout")
    login(client, school.pat)
    assert client.get(f"/media/{collector.photo_id}/thumb").status_code == 404


def test_parents_cannot_add_collectors(client, school):
    login(client, school.sam)
    response = client.post(f"/children/{school.ava.id}/collectors", data={"name": "Stranger"})
    assert response.status_code == 404
