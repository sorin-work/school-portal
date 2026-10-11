from flask import Blueprint, flash, redirect, render_template, url_for
from sqlalchemy import select

from .. import audit, retention
from ..decorators import admin_required
from ..extensions import db
from ..models import Child

bp = Blueprint("admin_retention", __name__, url_prefix="/admin/retention")


@bp.get("/")
@admin_required
def index():
    children = list(
        db.session.scalars(
            select(Child).where(Child.left_on.is_not(None)).order_by(Child.purge_after)
        )
    )
    return render_template("admin/retention.html", children=children)


@bp.post("/<int:child_id>/hold")
@admin_required
def toggle_hold(child_id: int):
    child = db.get_or_404(Child, child_id)
    child.retention_hold = not child.retention_hold
    audit.record("child.hold" if child.retention_hold else "child.hold_released", child)
    db.session.commit()
    flash(
        f"{child.display_name}: {'on hold' if child.retention_hold else 'hold released'}.",
        "success",
    )
    return redirect(url_for(".index"))


@bp.post("/<int:child_id>/delete")
@admin_required
def delete_now(child_id: int):
    child = db.get_or_404(Child, child_id)
    if child.left_on is None:
        flash("Only children who have left can be deleted.", "error")
        return redirect(url_for(".index"))
    if child.retention_hold:
        flash("Release the hold first.", "error")
        return redirect(url_for(".index"))
    name = child.display_name
    retention.purge_child(child, reason="manual")
    db.session.commit()
    flash(f"The record of {name} is deleted.", "success")
    return redirect(url_for(".index"))
