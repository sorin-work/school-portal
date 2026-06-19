from school_portal.extensions import db
from school_portal.models import Role

from ..conftest import PASSWORD, login, make_user


def test_change_name_and_phone(client, app):
    user = make_user(Role.PARENT)
    login(client, user)
    client.post(
        "/account/", data={"form": "details", "d-name": "Sam Reid", "d-phone": "0161 496 0000"}
    )
    db.session.refresh(user)
    assert (user.name, user.phone) == ("Sam Reid", "0161 496 0000")


def test_change_password_needs_the_current_one(client, app):
    user = make_user(Role.PARENT)
    login(client, user)
    response = client.post(
        "/account/",
        data={
            "form": "password",
            "p-current": "wrong",
            "p-password": "a new long password",
            "p-confirm": "a new long password",
        },
    )
    assert b"not your current password" in response.data
    client.post(
        "/account/",
        data={
            "form": "password",
            "p-current": PASSWORD,
            "p-password": "a new long password",
            "p-confirm": "a new long password",
        },
    )
    db.session.refresh(user)
    assert user.check_password("a new long password")
