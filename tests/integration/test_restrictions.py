from school_portal.extensions import db
from school_portal.models import Guardian, Role

from ..conftest import login, make_user


def test_limiting_access_needs_a_reason_and_records_who(client, school):
    mark = make_user(Role.PARENT, email="mark@example.com", name="Mark Reid")
    login(client, school.admin)
    base = f"/admin/children/{school.ava.id}/guardians"
    client.post(base, data={"g-email": mark.email, "g-relationship": "Father", "g-access": "none"})
    assert db.session.scalar(db.select(Guardian).where(Guardian.user_id == mark.id)) is None
    client.post(
        base,
        data={
            "g-email": mark.email,
            "g-relationship": "Father",
            "g-access": "none",
            "g-restriction_reason": "Court order FD25-0417",
        },
    )
    link = db.session.scalar(db.select(Guardian).where(Guardian.user_id == mark.id))
    assert link.access == "none"
    assert link.restricted_by_id == school.admin.id and link.restricted_at is not None
    assert link.restriction_reason == "Court order FD25-0417"


def test_changing_access_later(client, school):
    login(client, school.admin)
    link = school.ava.guardians[0]
    url = f"/admin/children/{school.ava.id}/guardians/{link.id}"
    response = client.post(url, data={"access": "read_only", "restriction_reason": ""})
    assert b"Give a reason" in response.data
    client.post(url, data={"access": "read_only", "restriction_reason": "Family request"})
    db.session.refresh(link)
    assert link.access == "read_only"
    client.post(url, data={"access": "full", "receives_summary": "y"})
    db.session.refresh(link)
    assert link.access == "full" and link.restriction_reason is None
    from school_portal.models import AuditEntry

    changes = db.session.scalars(
        db.select(AuditEntry).where(AuditEntry.action == "guardian.access_changed")
    ).all()
    assert [(c.details["before"], c.details["after"]) for c in changes] == [
        ("full", "read_only"),
        ("read_only", "full"),
    ]


def test_the_reason_is_for_administrators_only(client, school):
    mark = make_user(Role.PARENT, email="mark@example.com", name="Mark Reid")
    db.session.add(
        Guardian(
            child_id=school.ava.id,
            user_id=mark.id,
            access="none",
            restriction_reason="Court order FD25-0417",
        )
    )
    db.session.commit()
    login(client, school.amy)
    page = client.get(f"/children/{school.ava.id}").data
    assert b"No access" in page and b"FD25-0417" not in page
    client.post("/logout")
    login(client, mark)
    assert client.get(f"/children/{school.ava.id}").status_code == 404
