import io
from datetime import timedelta

from sqlalchemy import func, select

from school_portal import retention, timeutil
from school_portal.extensions import db
from school_portal.models import AuditEntry, Child, Event, Media

from ..conftest import login
from ..images import jpeg_with_exif


def test_marking_a_child_as_left_sets_the_deletion_date(client, school):
    login(client, school.admin)
    left = timeutil.today()
    client.post(f"/admin/children/{school.ava.id}/leave", data={"l-left_on": left.isoformat()})
    db.session.refresh(school.ava)
    assert school.ava.left_on == left
    assert school.ava.purge_after == left + timedelta(days=1095)
    assert school.ava.room_id is None
    # A child who has left drops out of the lists, but the family keeps access.
    client.post("/logout")
    login(client, school.amy)
    assert b"Ava" not in client.get(f"/rooms/{school.saplings.id}").data
    client.post("/logout")
    login(client, school.sam)
    assert client.get(f"/children/{school.ava.id}/diary").status_code == 200


def test_purge_removes_the_child_and_their_photos_but_keeps_shared_ones(client, school):
    school.ava.photo_consent = school.leon.photo_consent = "group"
    db.session.commit()
    login(client, school.amy)
    room = f"/rooms/{school.saplings.id}/observe"
    client.post(
        room,
        data={
            "child_ids": [str(school.ava.id)],
            "note": "Alone",
            "photos": [(io.BytesIO(jpeg_with_exif()), "a.jpg")],
        },
        content_type="multipart/form-data",
    )
    client.post(
        room,
        data={
            "child_ids": [str(school.ava.id), str(school.leon.id)],
            "note": "Pair",
            "photos": [(io.BytesIO(jpeg_with_exif()), "b.jpg")],
        },
        content_type="multipart/form-data",
    )
    client.get(f"/children/{school.ava.id}")
    assert db.session.scalar(select(func.count()).select_from(Media)) == 2
    ava_id = school.ava.id
    school.ava.left_on = timeutil.today() - timedelta(days=400)
    school.ava.purge_after = timeutil.today() - timedelta(days=1)
    db.session.commit()

    assert retention.purge_due() == 1
    db.session.expire_all()
    assert db.session.get(Child, ava_id) is None
    assert db.session.scalars(select(Event).where(Event.child_id == ava_id)).all() == []
    # The pair photo stays for Leon; Ava's own photo is gone, files too.
    (kept,) = db.session.scalars(select(Media))
    assert client.get(f"/media/{kept.id}").status_code == 200
    entries = db.session.scalars(select(AuditEntry).where(AuditEntry.child_id == ava_id)).all()
    purged = [e for e in entries if e.action == "child.purged"]
    assert purged and purged[0].details["photos_deleted"] == 1
    assert all(e.target is None for e in entries if e.action == "child.viewed")


def test_held_records_are_kept(school):
    school.ava.left_on = timeutil.today() - timedelta(days=400)
    school.ava.purge_after = timeutil.today() - timedelta(days=1)
    school.ava.retention_hold = True
    db.session.commit()
    assert retention.purge_due() == 0
    assert db.session.get(Child, school.ava.id) is not None


def test_children_still_on_the_roll_are_never_purged(school):
    assert retention.due(timeutil.today() + timedelta(days=10000)) == []
