from sqlalchemy import func, select

from school_portal.extensions import db
from school_portal.models import User


def test_create_admin(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--email",
            "Head@Example.com",
            "--name",
            "Head Teacher",
            "--password",
            "a long password",
        ]
    )
    assert result.exit_code == 0, result.output
    user = db.session.scalar(select(User).where(User.email == "head@example.com"))
    assert user.is_admin and user.check_password("a long password")


def test_seed_demo_only_fills_an_empty_database(app):
    runner = app.test_cli_runner()
    assert "Demo school created" in runner.invoke(args=["seed-demo"]).output
    count = db.session.scalar(select(func.count()).select_from(User))
    assert "leaving the database alone" in runner.invoke(args=["seed-demo"]).output
    assert db.session.scalar(select(func.count()).select_from(User)) == count
