import pytest

from school_portal import create_app
from school_portal.config import Config


def test_defaults(monkeypatch):
    monkeypatch.delenv("SEED_DEMO", raising=False)
    config = Config()
    assert config.SEED_DEMO is False
    assert config.SCHOOL_TIMEZONE == "Europe/London"


def test_booleans_from_the_environment(monkeypatch):
    monkeypatch.setenv("SEED_DEMO", "yes")
    monkeypatch.setenv("SHOW_DEMO_LOGINS", "0")
    config = Config()
    assert config.SEED_DEMO is True
    assert config.SHOW_DEMO_LOGINS is False


def test_production_needs_a_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app()
