from school_portal.extensions import db
from school_portal.models import Role, Room

from ..conftest import login, make_user


def test_only_administrators_manage_rooms(client, app):
    staff = make_user(Role.STAFF)
    login(client, staff)
    assert client.get("/admin/rooms/").status_code == 403


def test_create_a_room_with_staff(client, app):
    admin = make_user(Role.ADMIN)
    amy = make_user(Role.STAFF, name="Amy Lead")
    tom = make_user(Role.STAFF, name="Tom Helper")
    login(client, admin)
    response = client.post(
        "/admin/rooms/new",
        data={
            "name": "Saplings",
            "kind": "nursery",
            "age_range": "2 to 3",
            "capacity": "12",
            "sort_order": "1",
            "staff": [str(tom.id)],
            "leads": [str(amy.id)],
        },
    )
    assert response.status_code == 302
    room = db.session.scalar(db.select(Room).where(Room.name == "Saplings"))
    assert {(s.user_id, s.is_lead) for s in room.staff} == {(amy.id, True), (tom.id, False)}


def test_room_names_are_unique(client, app):
    admin = make_user(Role.ADMIN)
    login(client, admin)
    client.post("/admin/rooms/new", data={"name": "Oaks", "kind": "nursery"})
    response = client.post("/admin/rooms/new", data={"name": "Oaks", "kind": "class"})
    assert response.status_code == 200
    assert b"Another room has that name" in response.data
