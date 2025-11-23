"""Configuration read from the environment.

Everything has a default that works for local development, except the secret
key in production: create_app refuses to start without one when FLASK_ENV or
APP_ENV says production.
"""

import os


def _bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


class Config:
    def __init__(self) -> None:
        self.APP_ENV = os.environ.get("APP_ENV", "development")
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
        self.SQLALCHEMY_DATABASE_URI = os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://school:school@127.0.0.1:5463/school"
        )
        self.SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
        self.BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:4433").rstrip("/")
        self.SEED_DEMO = _bool("SEED_DEMO")
        self.SHOW_DEMO_LOGINS = _bool("SHOW_DEMO_LOGINS")
        self.WTF_CSRF_TIME_LIMIT = None
        self.SCHOOL_NAME = os.environ.get("SCHOOL_NAME", "School Portal")
        self.SCHOOL_TIMEZONE = os.environ.get("SCHOOL_TIMEZONE", "Europe/London")
        self.TESTING = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"
