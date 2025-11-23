from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    try:
        db.session.execute(text("select 1"))
    except Exception:  # pragma: no cover - only when the database is down
        return jsonify(status="error", database="unreachable"), 503
    return jsonify(status="ok", database="ok")
