from flask import Flask

from .config import Config
from .extensions import csrf, db, login_manager


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    config = Config()
    app.config.from_object(config)
    if overrides:
        app.config.update(overrides)
    if config.is_production and app.config["SECRET_KEY"] == "dev-secret-change-me":
        raise RuntimeError("Set SECRET_KEY before running in production")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    csrf.init_app(app)

    from . import models  # noqa: F401  (registers the tables)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(models.User, int(user_id))

    _register_blueprints(app)
    _register_template_helpers(app)
    _register_error_pages(app)
    from .cli import register_cli

    register_cli(app)
    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints import health

    app.register_blueprint(health.bp)
    from .blueprints import auth

    app.register_blueprint(auth.bp)
    from .blueprints import dashboard

    app.register_blueprint(dashboard.bp)
    from .blueprints import admin_rooms

    app.register_blueprint(admin_rooms.bp)
    from .blueprints import admin_children

    app.register_blueprint(admin_children.bp)
    from .blueprints import admin_users

    app.register_blueprint(admin_users.bp)
    from .blueprints import children

    app.register_blueprint(children.bp)
    from .blueprints import room_view

    app.register_blueprint(room_view.bp)
    from .blueprints import timeline

    app.register_blueprint(timeline.bp)
    from .blueprints import media

    app.register_blueprint(media.bp)
    from .blueprints import attendance

    app.register_blueprint(attendance.bp)


def _register_error_pages(app: Flask) -> None:
    from flask import render_template, request

    def page(code: int, title: str, text: str):
        def handler(_error):
            if request.headers.get("HX-Request"):
                return title, code
            return render_template("errors/error.html", code=code, title=title, text=text), code

        return handler

    app.register_error_handler(
        400, page(400, "Bad request", "The form was out of date or incomplete.")
    )
    app.register_error_handler(403, page(403, "Not allowed", "Your account cannot open this page."))
    app.register_error_handler(404, page(404, "Not found", "There is nothing at this address."))
    app.register_error_handler(
        413, page(413, "Too large", "The upload is too large. Try fewer or smaller photos.")
    )


def _register_template_helpers(app: Flask) -> None:
    from . import timeutil

    app.jinja_env.filters["time"] = timeutil.fmt_time
    app.jinja_env.filters["date"] = timeutil.fmt_date
    app.jinja_env.filters["datetime"] = timeutil.fmt_datetime
    app.jinja_env.filters["day"] = timeutil.fmt_day
    app.jinja_env.filters["isoday"] = timeutil.fmt_isoday

    @app.context_processor
    def inject_globals():
        school_name = app.config["SCHOOL_NAME"]
        values = {"school_name": school_name, "today": timeutil.today()}
        return values
