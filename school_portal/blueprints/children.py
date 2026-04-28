from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField
from wtforms.validators import DataRequired, Length, Optional

from .. import access
from ..extensions import db
from ..models import Collector
from ..uploads import UploadError, save_image

bp = Blueprint("children", __name__, url_prefix="/children")


class CollectorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    relationship = StringField("Relationship", validators=[Optional(), Length(max=40)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    password_hint = StringField("Collection password", validators=[Optional(), Length(max=80)])
    photo = FileField("Photo")


@bp.get("/<int:child_id>")
@login_required
def show(child_id: int):
    child = access.child_or_404(child_id)
    show_medical = access.can_see_medical(current_user, child)
    guardians = child.guardians if current_user.is_staff else []
    collectors = [c for c in db.session.query(Collector).filter_by(child_id=child.id) if c.active]
    form = CollectorForm() if current_user.is_staff else None
    return render_template(
        "children/show.html",
        child=child,
        show_medical=show_medical,
        guardians=guardians,
        collectors=collectors,
        form=form,
    )


@bp.post("/<int:child_id>/collectors")
@login_required
def add_collector(child_id: int):
    if not current_user.is_staff:
        abort(404)
    child = access.child_or_404(child_id)
    form = CollectorForm()
    if not form.validate_on_submit():
        flash("Give the collector's name.", "error")
        return redirect(url_for(".show", child_id=child.id) + "#collectors")
    collector = Collector(
        child_id=child.id,
        name=form.name.data.strip(),
        relationship_label=form.relationship.data or None,
        phone=form.phone.data or None,
        password_hint=form.password_hint.data or None,
    )
    if form.photo.data and form.photo.data.filename:
        try:
            collector.photo = save_image(
                form.photo.data, purpose="collector", user_id=current_user.id
            )
        except UploadError as exc:
            flash(str(exc), "error")
            return redirect(url_for(".show", child_id=child.id) + "#collectors")
    db.session.add(collector)
    db.session.commit()
    flash(f"{collector.name} can now collect {child.display_name}.", "success")
    return redirect(url_for(".show", child_id=child.id) + "#collectors")


@bp.post("/<int:child_id>/collectors/<int:collector_id>/remove")
@login_required
def remove_collector(child_id: int, collector_id: int):
    if not current_user.is_staff:
        abort(404)
    child = access.child_or_404(child_id)
    collector = db.session.get(Collector, collector_id)
    if collector is None or collector.child_id != child.id:
        abort(404)
    collector.active = False
    db.session.commit()
    flash(f"{collector.name} removed from the collectors.", "success")
    return redirect(url_for(".show", child_id=child.id) + "#collectors")
