import io
import json
import zipfile

from school_portal.extensions import db

from ..conftest import login


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


def test_only_administrators_export(client, school):
    login(client, school.amy)
    assert client.post(f"/admin/children/{school.ava.id}/export").status_code == 403
