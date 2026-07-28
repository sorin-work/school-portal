from sqlalchemy import select

from school_portal.extensions import db
from school_portal.models import AuditEntry

from ..conftest import login


def entries(child=None):
    query = select(AuditEntry).order_by(AuditEntry.id)
    if child is not None:
        query = query.where(AuditEntry.child_id == child.id)
    return list(db.session.scalars(query))


def test_staff_views_are_recorded_once_per_window(client, school):
    login(client, school.amy)
    client.get(f"/children/{school.ava.id}")
    client.get(f"/children/{school.ava.id}")
    client.get(f"/children/{school.ava.id}/diary")
    actions = [(e.action, e.target, e.actor_id) for e in entries(school.ava)]
    assert actions == [
        ("child.viewed", "profile", school.amy.id),
        ("child.viewed", "diary", school.amy.id),
    ]


def test_parents_looking_at_their_own_child_are_not_logged(client, school):
    login(client, school.sam)
    client.get(f"/children/{school.ava.id}/diary")
    assert entries() == []


def test_changes_are_recorded_with_the_fields(client, school):
    login(client, school.admin)
    data = {
        "first_name": "Ava",
        "last_name": "Reid",
        "date_of_birth": "2023-03-14",
        "room_id": str(school.saplings.id),
        "key_person_id": "0",
        "allergies": "Peanuts",
        "photo_consent": "none",
    }
    client.post(f"/admin/children/{school.ava.id}", data=data)
    change = [e for e in entries(school.ava) if e.action == "child.updated"][0]
    assert change.details == {"fields": ["allergies"]}
    assert change.actor_id == school.admin.id


def test_the_log_page_filters_by_child(client, school):
    login(client, school.amy)
    client.get(f"/children/{school.ava.id}")
    client.get(f"/children/{school.leon.id}")
    client.post("/logout")
    login(client, school.admin)
    page = client.get(f"/admin/audit/?child={school.ava.id}").data
    assert b"Ava Reid" in page and b"Leon" not in page
    client.post("/logout")
    login(client, school.amy)
    assert client.get("/admin/audit/").status_code == 403
