from flask import Blueprint, render_template, request
from sqlalchemy import select

from ..decorators import admin_required
from ..extensions import db
from ..models import AuditEntry, Child

bp = Blueprint("admin_audit", __name__, url_prefix="/admin/audit")

PAGE = 100


@bp.get("/")
@admin_required
def index():
    query = select(AuditEntry).order_by(AuditEntry.id.desc())
    child_id = request.args.get("child", type=int)
    child = None
    if child_id:
        query = query.where(AuditEntry.child_id == child_id)
        child = db.session.get(Child, child_id)
    action = request.args.get("action", "").strip()
    before = request.args.get("before", type=int)
    if before:
        query = query.where(AuditEntry.id < before)
    entries = list(db.session.scalars(query.limit(PAGE)))
    names = {}
    ids = {e.child_id for e in entries if e.child_id}
    if ids:
        names = {
            c.id: c.display_name for c in db.session.scalars(select(Child).where(Child.id.in_(ids)))
        }
    return render_template(
        "admin/audit.html",
        entries=entries,
        names=names,
        child=child,
        child_id=child_id,
        action=action,
        more=len(entries) == PAGE,
    )
