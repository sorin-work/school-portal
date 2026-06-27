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


def test_choose_which_children_get_a_summary(client, school):
    from school_portal.models import Guardian

    from ..conftest import link

    link(school.sam, school.leon)
    login(client, school.sam)
    client.post("/account/summaries", data={"child_ids": [str(school.ava.id)]})
    rows = db.session.scalars(db.select(Guardian).where(Guardian.user_id == school.sam.id)).all()
    assert {g.child_id: g.receives_summary for g in rows} == {
        school.ava.id: True,
        school.leon.id: False,
    }
