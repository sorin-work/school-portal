from school_portal.extensions import db
from school_portal.models import Role
from school_portal.notify import notify

from ..conftest import login, make_user


def test_list_open_and_mark_read(client, app):
    user = make_user(Role.PARENT)
    notify([user, user], "notice", "Sports day moved", "/notices/")
    db.session.commit()
    login(client, user)
    page = client.get("/notifications/")
    assert page.data.count(b"Sports day moved") == 1
    from school_portal.models import Notification

    item = db.session.scalar(db.select(Notification))
    response = client.get(f"/notifications/{item.id}")
    assert response.headers["Location"] == "/notices/"
    assert item.read_at is not None


def test_someone_elses_notification_is_not_opened(client, app):
    owner = make_user(Role.PARENT)
    other = make_user(Role.PARENT)
    notify([owner], "notice", "Private", "/notices/")
    db.session.commit()
    from school_portal.models import Notification

    item = db.session.scalar(db.select(Notification))
    login(client, other)
    client.get(f"/notifications/{item.id}")
    assert item.read_at is None


def test_only_local_links_are_followed(client, app):
    user = make_user(Role.PARENT)
    notify([user], "x", "Odd", "https://example.com/")
    db.session.commit()
    from school_portal.models import Notification

    item = db.session.scalar(db.select(Notification))
    login(client, user)
    assert client.get(f"/notifications/{item.id}").headers["Location"] == "/notifications/"
