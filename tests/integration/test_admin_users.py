from school_portal.extensions import db
from school_portal.models import Role, User

from ..conftest import login, make_user


def test_create_and_edit_an_account(client, app):
    admin = make_user(Role.ADMIN)
    login(client, admin)
    response = client.post(
        "/admin/users/new",
        data={"name": "Tom Becker", "email": "Tom@Example.com", "role": "staff", "active": "y"},
    )
    assert response.status_code == 302
    user = db.session.scalar(db.select(User).where(User.email == "tom@example.com"))
    assert user.role == "staff" and user.active
    client.post(
        f"/admin/users/{user.id}",
        data={"name": "Tom Becker", "email": "tom@example.com", "role": "staff"},
    )
    db.session.refresh(user)
    assert user.active is False


def test_addresses_are_unique(client, app):
    admin = make_user(Role.ADMIN)
    taken = make_user(Role.PARENT, email="taken@example.com")
    login(client, admin)
    response = client.post(
        "/admin/users/new", data={"name": "Copy", "email": taken.email.upper(), "role": "parent"}
    )
    assert b"Another account uses that address" in response.data


def test_role_filter(client, app):
    admin = make_user(Role.ADMIN, name="Ada Admin")
    make_user(Role.PARENT, name="Pat Parent")
    login(client, admin)
    page = client.get("/admin/users/?role=parent").data
    assert b"Pat Parent" in page and b"Ada Admin</a>" not in page
