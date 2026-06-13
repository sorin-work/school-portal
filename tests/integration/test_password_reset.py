import re

from school_portal.models import Role

from ..conftest import login, make_user


def sent(app):
    return app.extensions.get("outbox", [])


def reset_link(message) -> str:
    return re.search(r"https?://[^/]+(/reset/\S+)", message.get_content()).group(1)


def test_reset_by_email(client, app):
    user = make_user(Role.PARENT, email="sam@example.com")
    client.post("/forgot", data={"email": "Sam@example.com"})
    (message,) = sent(app)
    assert message["To"] == "sam@example.com"
    link = reset_link(message)
    response = client.post(link, data={"password": "a brand new one", "confirm": "a brand new one"})
    assert response.status_code == 302
    assert login(client, user, "a brand new one").status_code == 302


def test_a_link_works_once(client, app):
    make_user(Role.PARENT, email="sam@example.com")
    client.post("/forgot", data={"email": "sam@example.com"})
    link = reset_link(sent(app)[0])
    client.post(link, data={"password": "first new one", "confirm": "first new one"})
    response = client.post(link, data={"password": "second new one", "confirm": "second new one"})
    assert response.status_code == 302
    assert "/forgot" in response.headers["Location"]


def test_unknown_addresses_get_the_same_answer_and_no_mail(client, app):
    response = client.post("/forgot", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert b"If that address has an account" in response.data
    assert sent(app) == []


def test_resets_are_limited_per_hour(client, app):
    make_user(Role.PARENT, email="sam@example.com")
    for _ in range(5):
        client.post("/forgot", data={"email": "sam@example.com"})
    assert len(sent(app)) == 3


def test_short_passwords_are_refused(client, app):
    make_user(Role.PARENT, email="sam@example.com")
    client.post("/forgot", data={"email": "sam@example.com"})
    link = reset_link(sent(app)[0])
    response = client.post(link, data={"password": "short", "confirm": "short"})
    assert b"at least 10 characters" in response.data
