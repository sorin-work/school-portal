from school_portal import settings
from school_portal.extensions import db


def test_defaults_until_saved(app):
    assert settings.get("summary_time") == "17:30"
    assert settings.get_bool("summary_enabled") is True
    assert settings.get("school_name") == app.config["SCHOOL_NAME"]


def test_saved_values_win(app):
    settings.put("summary_enabled", False)
    settings.put("retention_days", 365)
    db.session.commit()
    assert settings.get_bool("summary_enabled") is False
    assert settings.get_int("retention_days") == 365


def test_unknown_keys_are_refused(app):
    import pytest

    with pytest.raises(KeyError):
        settings.put("colour_scheme", "green")
