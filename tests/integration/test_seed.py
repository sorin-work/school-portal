from sqlalchemy import func, select

from school_portal.extensions import db
from school_portal.models import Child, User
from school_portal.seed import seed

from ..conftest import login


def test_demo_school_and_logins(client, app):
    seed()
    assert db.session.scalar(select(func.count()).select_from(Child)) == 16
    admin = db.session.scalar(select(User).where(User.email == "demo@example.com"))
    assert admin.is_admin
    assert login(client, admin, "demo-password").status_code == 302
    assert client.get("/").status_code == 200
    client.post("/logout")
    parent = db.session.scalar(select(User).where(User.email == "parent@example.com"))
    login(client, parent, "demo-password")
    page = client.get("/").data
    assert b"Ava Reid" in page and b"Noah Reid" in page
