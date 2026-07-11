from school_portal.extensions import db
from school_portal.models import Notice, Notification

from ..conftest import login


def test_admin_posts_to_the_whole_school(client, school):
    login(client, school.admin)
    response = client.post(
        "/notices/new", data={"title": "Wellies please", "body": "Named, please."}
    )
    assert response.status_code == 302
    client.post("/logout")
    for parent in (school.sam, school.pat):
        login(client, parent)
        assert b"Wellies please" in client.get("/notices/").data
        client.post("/logout")
    assert {n.user_id for n in db.session.scalars(db.select(Notification))} == {
        school.sam.id,
        school.pat.id,
    }


def test_room_notices_reach_only_that_room(client, school):
    login(client, school.amy)  # a lead in Saplings
    client.post(
        "/notices/new",
        data={
            "title": "Saplings photo week",
            "body": "Bring a photo",
            "rooms": [str(school.saplings.id)],
        },
    )
    notice = db.session.scalar(db.select(Notice))
    client.post("/logout")
    login(client, school.sam)
    assert b"Saplings photo week" in client.get("/notices/").data
    client.post("/logout")
    login(client, school.pat)
    assert b"Saplings photo week" not in client.get("/notices/").data
    assert client.get(f"/notices/{notice.id}").status_code == 404
    assert {n.user_id for n in db.session.scalars(db.select(Notification))} == {school.sam.id}


def test_staff_who_lead_no_room_cannot_post(client, school):
    login(client, school.ben)
    assert client.get("/notices/new").status_code == 403


def test_leads_post_only_to_their_rooms(client, school):
    login(client, school.amy)
    response = client.post(
        "/notices/new", data={"title": "Oaks?", "body": "x", "rooms": [str(school.oaks.id)]}
    )
    assert response.status_code == 200
    assert db.session.scalar(db.select(Notice)) is None
