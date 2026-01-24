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
