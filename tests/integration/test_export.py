import io
import json
import zipfile

from school_portal.extensions import db

from ..conftest import login
from ..images import jpeg_with_exif


def test_export_holds_the_record(client, school):
    school.ava.medical_notes = "Inhaler"
    db.session.commit()
    login(client, school.sam)
    client.post(f"/children/{school.ava.id}/messages", data={"body": "Hello from home"})
    client.post("/logout")
    login(client, school.admin)
    link = school.ava.guardians[0]
    response = client.post(f"/admin/children/{school.ava.id}/export", data={"guardian_id": link.id})
    assert response.mimetype == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.data))
    record = json.loads(archive.read("record.json"))
    assert record["child"]["medical_notes"] == "Inhaler"
    assert record["messages"][0]["body"] == "Hello from home"
    assert record["requested_by"] == "Sam Reid"
    assert "index.html" in archive.namelist()


def test_only_administrators_export(client, school):
    login(client, school.amy)
    assert client.post(f"/admin/children/{school.ava.id}/export").status_code == 403


def test_export_leaves_out_photos_other_consent_forbids(client, school):
    school.ava.photo_consent = "group"
    school.leon.photo_consent = "own"
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
    client.post("/logout")
    login(client, school.admin)
    response = client.post(f"/admin/children/{school.ava.id}/export", data={"guardian_id": ""})
    archive = zipfile.ZipFile(io.BytesIO(response.data))
    photos = [n for n in archive.namelist() if n.startswith("photos/")]
    assert len(photos) == 1
    assert json.loads(archive.read("record.json"))["photos_withheld"] == 1
