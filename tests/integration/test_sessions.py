from school_portal import settings
from school_portal.extensions import db
from school_portal.models import Role

from ..conftest import login, make_user


def test_idle_sessions_end(client, app):
    user = make_user(Role.STAFF)
    login(client, user)
    assert client.get("/").status_code == 200
    with client.session_transaction() as session:
        session["seen"] -= 61 * 60
    response = client.get("/")
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_the_idle_limit_is_a_setting(client, app):
    settings.put("idle_timeout_minutes", 120)
    db.session.commit()
    user = make_user(Role.STAFF)
    login(client, user)
    with client.session_transaction() as session:
        session["seen"] -= 90 * 60
    assert client.get("/").status_code == 200


def test_polling_for_notifications_does_not_keep_a_session_alive(client, app):
    user = make_user(Role.STAFF)
    login(client, user)
    with client.session_transaction() as session:
        session["seen"] -= 30 * 60
        before = session["seen"]
    client.get("/notifications/count")
    with client.session_transaction() as session:
        assert session["seen"] == before


def test_sign_out_everywhere(client, app):
    user = make_user(Role.PARENT)
    other = app.test_client()
    login(client, user)
    login(other, user)
    client.post("/account/sign-out-everywhere")
    assert other.get("/").status_code == 302
    assert client.get("/").status_code == 302


def test_changing_the_password_keeps_this_device_only(client, app):
    user = make_user(Role.PARENT)
    other = app.test_client()
    login(client, user)
    login(other, user)
    client.post(
        "/account/",
        data={
            "form": "password",
            "p-current": "correct horse battery",
            "p-password": "a new long password",
            "p-confirm": "a new long password",
        },
    )
    assert client.get("/").status_code == 200
    assert other.get("/").status_code == 302


def test_admin_signs_someone_out(client, app):
    admin = make_user(Role.ADMIN)
    user = make_user(Role.PARENT)
    other = app.test_client()
    login(other, user)
    login(client, admin)
    client.post(f"/admin/users/{user.id}/sign-out")
    assert other.get("/").status_code == 302
