"""Sessions end after a fixed lifetime and after a period without activity.

The lifetime is SESSION_MAX_HOURS (the cookie's permanent lifetime). The idle
limit is the "idle_timeout_minutes" setting, checked on every request, so a
tablet left signed in on a shelf is signed out on its own.
"""

from flask import Flask, flash, redirect, request, session, url_for
from flask_login import current_user, logout_user

from . import settings, timeutil

SKIP = {"static", "health.healthz"}
# Requests the page makes on its own; they must not count as activity.
PASSIVE = {"notifications.count"}


def start_session() -> None:
    session.permanent = True
    session["seen"] = int(timeutil.now().timestamp())


def init_sessions(app: Flask) -> None:
    @app.before_request
    def check_idle():
        if request.endpoint in SKIP or not current_user.is_authenticated:
            return None
        now = int(timeutil.now().timestamp())
        seen = session.get("seen")
        limit = settings.get_int("idle_timeout_minutes") * 60
        if seen is not None and now - seen > limit:
            session.clear()
            logout_user()
            flash("You were signed out after a period of inactivity.", "info")
            if request.headers.get("HX-Request"):
                return "", 204, {"HX-Redirect": url_for("auth.login")}
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        if request.endpoint not in PASSIVE:
            session["seen"] = now
        return None
