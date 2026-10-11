import click
from flask import Flask
from sqlalchemy import func, select

from .extensions import db
from .models import Role, User


def register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.password_option()
    def create_admin(email: str, name: str, password: str) -> None:
        """Create an administrator account, or make an existing one an administrator."""
        email = email.strip().lower()
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            user = User(email=email, name=name.strip(), role=Role.ADMIN)
            db.session.add(user)
        user.role = Role.ADMIN
        user.active = True
        user.set_password(password)
        db.session.commit()
        click.echo(f"{email} is an administrator.")

    @app.cli.command("seed-demo")
    @click.option("--force", is_flag=True, help="Seed even if there are users already.")
    def seed_demo(force: bool) -> None:
        """Fill an empty database with the invented demo school."""
        from .seed import seed

        if not force and db.session.scalar(select(func.count()).select_from(User)):
            click.echo("There are users already, leaving the database alone.")
            return
        seed()
        click.echo("Demo school created. Sign in as demo@example.com / demo-password.")

    @app.cli.command("worker")
    @click.option("--poll", default=5.0, help="Seconds to wait when there is nothing to do.")
    def worker(poll: float) -> None:
        """Run background jobs until stopped."""
        import logging

        from .jobs import work_forever

        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        work_forever(poll)

    @app.cli.command("run-jobs")
    def run_jobs() -> None:
        """Queue what is due and run the queue once, then exit."""
        from .jobs import run_due, schedule

        schedule()
        click.echo(f"Ran {run_due(limit=500)} jobs.")

    @app.cli.command("purge-leavers")
    def purge_leavers() -> None:
        """Delete the records of children whose retention period is over."""
        from .retention import purge_due

        click.echo(f"Deleted {purge_due()} records.")
