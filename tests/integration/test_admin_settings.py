from school_portal import settings
from school_portal.extensions import db
from school_portal.models import Role

from ..conftest import login, make_user


def test_save_the_settings(client, app):
    login(client, make_user(Role.ADMIN))
    response = client.post(
        "/admin/settings/",
        data={
            "school_name": "Willow Brook",
            "summary_enabled": "y",
            "summary_time": "16:45",
            "retention_days": "730",
            "idle_timeout_minutes": "30",
        },
    )
    assert response.status_code == 302
    db.session.expire_all()
    assert settings.get("school_name") == "Willow Brook"
    assert settings.get("summary_time") == "16:45"
    assert settings.get_int("retention_days") == 730
    assert b"Willow Brook" in client.get("/").data


def test_bad_values_are_refused(client, app):
    login(client, make_user(Role.ADMIN))
    response = client.post(
        "/admin/settings/",
        data={
            "school_name": "X",
            "summary_time": "25:00",
            "retention_days": "1",
            "idle_timeout_minutes": "30",
        },
    )
    assert b"Use HH:MM" in response.data
    assert settings.get("summary_time") == "17:30"


def test_only_administrators(client, app):
    login(client, make_user(Role.STAFF))
    assert client.get("/admin/settings/").status_code == 403
