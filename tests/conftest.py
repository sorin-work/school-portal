"""Shared fixtures.

Integration tests run against PostgreSQL (TEST_DATABASE_URL). The schema is
built once per run with the Alembic migrations, so the migrations are tested
too, and every table is emptied after each test.
"""

import os

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text

from school_portal import create_app
from school_portal.extensions import db
from school_portal.models import Role, User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://school:school@127.0.0.1:5463/school_test"
)
PASSWORD = "correct horse battery"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def database():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    config = AlembicConfig(os.path.join(ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(ROOT, "migrations"))
    config.attributes["url"] = TEST_DATABASE_URL
    config.attributes["skip_logging"] = True
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture
def app(database, tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test",
            "SERVER_NAME": "portal.test",
            # A fast hash: the tests make hundreds of accounts.
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
        }
    )

    def forget_cached_state():
        # The tests hold one app context for the whole test, so values cached
        # on g would leak from one request (and one signed-in user) to the next.
        from flask import g

        g.pop("_login_user", None)
        g.pop("settings", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_state)
    with app.app_context():
        yield app
        db.session.remove()
        tables = ", ".join(f'"{t.name}"' for t in db.metadata.sorted_tables)
        with db.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(role: str = Role.PARENT, email: str | None = None, name: str | None = None) -> User:
    count = db.session.query(User).count() + 1
    user = User(
        email=email or f"{role}{count}@example.com",
        name=name or f"{role.title()} Number{count}",
        role=role,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user: User, password: str = PASSWORD):
    return client.post("/login", data={"email": user.email, "password": password})
