from sqlalchemy import select

from school_portal.extensions import db
from school_portal.models import Message

from ..conftest import link, login, make_user


def test_parent_and_staff_talk_about_a_child(client, school):
    login(client, school.sam)
    response = client.post(f"/children/{school.ava.id}/messages", data={"body": "She has a cough"})
    assert response.status_code == 200
    client.post("/logout")
    login(client, school.amy)
    assert b"She has a cough" in client.get("/messages").data
    client.post(f"/children/{school.ava.id}/messages", data={"body": "Thanks, we will watch her"})
    client.post("/logout")
    login(client, school.sam)
    page = client.get(f"/children/{school.ava.id}/messages").data
    assert b"She has a cough" in page and b"we will watch her" in page


def test_messages_stay_with_their_child(client, school):
    login(client, school.sam)
    client.post(f"/children/{school.ava.id}/messages", data={"body": "About Ava"})
    client.post("/logout")
    login(client, school.pat)
    assert b"About Ava" not in client.get("/messages").data
    assert client.get(f"/children/{school.ava.id}/messages").status_code == 404
    assert client.post(f"/children/{school.ava.id}/messages", data={"body": "x"}).status_code == 404
    client.post("/logout")
    login(client, school.ben)
    assert b"About Ava" not in client.get("/messages").data


def test_read_only_guardians_read_but_cannot_post(client, school):
    gran = make_user("parent", email="gran@example.com")
    link(gran, school.ava, access="read_only")
    login(client, gran)
    page = client.get(f"/children/{school.ava.id}/messages")
    assert page.status_code == 200
    assert b"not reply" in page.data
    assert (
        client.post(f"/children/{school.ava.id}/messages", data={"body": "hi"}).status_code == 404
    )
    assert db.session.scalars(select(Message)).all() == []


def test_empty_and_huge_messages_are_refused(client, school):
    login(client, school.sam)
    assert (
        client.post(f"/children/{school.ava.id}/messages", data={"body": "  "}).status_code == 400
    )
    response = client.post(f"/children/{school.ava.id}/messages", data={"body": "x" * 4001})
    assert response.status_code == 400


def test_a_message_notifies_the_other_side(client, school):
    from school_portal.models import Notification

    login(client, school.sam)
    client.post(f"/children/{school.ava.id}/messages", data={"body": "Hello"})
    users = {n.user_id for n in db.session.scalars(select(Notification))}
    assert users == {school.amy.id}
    client.post("/logout")
    login(client, school.amy)
    assert b'badge-red">1<' in client.get("/notifications/count").data
    client.post("/notifications/read")
    assert b"badge" not in client.get("/notifications/count").data
