from flask import Blueprint, Response, abort, render_template, request

from .. import audit, timeutil
from ..decorators import admin_required
from ..export import build_zip
from ..extensions import db
from ..models import Child, Guardian

bp = Blueprint("exports", __name__, url_prefix="/admin/children")


@bp.get("/<int:child_id>/export")
@admin_required
def form(child_id: int):
    child = db.get_or_404(Child, child_id)
    return render_template("exports/form.html", child=child)


@bp.post("/<int:child_id>/export")
@admin_required
def download(child_id: int):
    child = db.get_or_404(Child, child_id)
    guardian_id = request.form.get("guardian_id", type=int)
    link = db.session.get(Guardian, guardian_id) if guardian_id else None
    if link is not None and link.child_id != child.id:
        abort(404)
    data = build_zip(child, link)
    audit.record(
        "export.created",
        child,
        target=f"user:{link.user_id}" if link else None,
        size=len(data),
    )
    db.session.commit()
    stamp = timeutil.today().isoformat()
    filename = f"record-{child.id}-{stamp}.zip"
    return Response(
        data,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "private, no-store",
        },
    )
