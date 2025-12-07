from school_portal.models import Role

from ..conftest import PASSWORD, login, make_user


def test_sign_in_and_out(client, app):
    user = make_user(Role.STAFF, email="amy@example.com")
    response = login(client, user)
    assert response.status_code == 302
    page = client.get("/")
    assert page.status_code == 200
    assert user.first_name.encode() in page.data
    response = client.post("/logout")
    assert response.status_code == 302
    assert client.get("/").status_code == 302


def test_wrong_password_is_refused(client, app):
    user = make_user(Role.PARENT)
    response = client.post("/login", data={"email": user.email, "password": "nope"})
    assert response.status_code == 401
    assert b"do not match" in response.data


def test_unknown_address_gets_the_same_answer(client, app):
    response = client.post("/login", data={"email": "nobody@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert b"do not match" in response.data


def test_disabled_accounts_cannot_sign_in(client, app):
    from school_portal.extensions import db

    user = make_user(Role.PARENT)
    user.active = False
    db.session.commit()
    assert login(client, user).status_code == 401


def test_pages_need_a_sign_in(client, app):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_next_only_follows_local_paths(client, app):
    user = make_user(Role.STAFF)
    response = client.post(
        "/login?next=//evil.example/", data={"email": user.email, "password": PASSWORD}
    )
    assert response.headers["Location"] == "/"


def test_email_is_not_case_sensitive(client, app):
    user = make_user(Role.PARENT, email="sam@example.com")
    response = client.post("/login", data={"email": "Sam@Example.COM", "password": PASSWORD})
    assert response.status_code == 302
    assert user.last_login_at is not None


def test_forms_need_a_csrf_token(app):
    app.config["WTF_CSRF_ENABLED"] = True
    user = make_user(Role.STAFF)
    client = app.test_client()
    response = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code in (200, 400)
    assert client.get("/").status_code == 302
