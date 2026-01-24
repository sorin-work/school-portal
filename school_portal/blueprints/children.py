from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .. import access

bp = Blueprint("children", __name__, url_prefix="/children")


@bp.get("/<int:child_id>")
@login_required
def show(child_id: int):
    child = access.child_or_404(child_id)
    show_medical = access.can_see_medical(current_user, child)
    guardians = child.guardians if current_user.is_staff else []
    collectors, form = [], None
    return render_template(
        "children/show.html",
        child=child,
        show_medical=show_medical,
        guardians=guardians,
        collectors=collectors,
        form=form,
    )
