from school_portal.extensions import db
from school_portal.models import Child, Role

from ..conftest import login, make_child, make_room, make_user


def test_add_a_child(client, app):
    admin = make_user(Role.ADMIN)
    room = make_room("Acorns")
    login(client, admin)
    response = client.post(
        "/admin/children/new",
        data={
            "first_name": "Mila",
            "last_name": "Nair",
            "date_of_birth": "2024-09-01",
            "room_id": str(room.id),
            "key_person_id": "0",
            "allergies": "Egg",
            "medical_notes": "Inhaler in the office",
        },
    )
    assert response.status_code == 302
    child = db.session.scalar(db.select(Child).where(Child.first_name == "Mila"))
    assert child.room_id == room.id
    assert child.has_allergies
    assert child.share_medical_with_parents is False


def test_children_list_and_search(client, app):
    admin = make_user(Role.ADMIN)
    login(client, admin)
    for first in ("Mila", "Theo"):
        client.post(
            "/admin/children/new",
            data={
                "first_name": first,
                "last_name": "X",
                "date_of_birth": "2024-01-01",
                "room_id": "0",
                "key_person_id": "0",
            },
        )
    page = client.get("/admin/children/?q=mil")
    assert b"Mila X</a>" in page.data
    assert b"Theo X</a>" not in page.data


def test_staff_cannot_open_the_admin_pages(client, app):
    login(client, make_user(Role.STAFF))
    assert client.get("/admin/children/").status_code == 403


def test_link_an_existing_parent(client, app):
    admin = make_user(Role.ADMIN)
    parent = make_user(Role.PARENT, email="sam@example.com")
    child = make_child()
    login(client, admin)
    response = client.post(
        f"/admin/children/{child.id}/guardians",
        data={"g-email": "SAM@example.com", "g-relationship": "Mother", "g-access": "full"},
    )
    assert response.status_code == 302
    assert [(g.user_id, g.relationship_label) for g in child.guardians] == [(parent.id, "Mother")]


def test_staff_accounts_cannot_be_guardians(client, app):
    admin = make_user(Role.ADMIN)
    staff = make_user(Role.STAFF)
    child = make_child()
    login(client, admin)
    client.post(
        f"/admin/children/{child.id}/guardians",
        data={"g-email": staff.email, "g-relationship": "Parent", "g-access": "full"},
    )
    assert child.guardians == []


def test_a_new_address_gets_an_account_and_an_invitation(client, app):
    from school_portal.models import User

    admin = make_user(Role.ADMIN)
    child = make_child()
    login(client, admin)
    client.post(
        f"/admin/children/{child.id}/guardians",
        data={
            "g-email": "new@example.com",
            "g-name": "Nia New",
            "g-relationship": "Father",
            "g-access": "full",
        },
    )
    user = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
    assert user.role == "parent" and user.password_hash is None
    from school_portal.jobs import run_due

    run_due()
    outbox = app.extensions["outbox"]
    assert outbox[-1]["To"] == "new@example.com"
    assert "/reset/" in outbox[-1].get_content()
