from flask import Flask

from .config import Config
from .extensions import db, login_manager


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

    from . import models  # noqa: F401  (registers the tables)

    _register_blueprints(app)
    _register_template_helpers(app)
    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints import health

    app.register_blueprint(health.bp)


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
