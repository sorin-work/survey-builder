"""The signed-in owner's own account."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from .auth import EMAIL_RE, normalize_email
from .extensions import db
from .models import User

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.before_request
@login_required
def _require_login():
    pass


@bp.route("/", methods=["GET", "POST"])
def profile():
    form = {"name": current_user.name, "email": current_user.email}
    errors: dict[str, str] = {}
    if request.method == "POST":
        form = {
            "name": request.form.get("name", "").strip(),
            "email": normalize_email(request.form.get("email", "")),
        }
        if not form["name"]:
            errors["name"] = "Please enter your name."
        elif len(form["name"]) > 120:
            errors["name"] = "Name must be at most 120 characters."
        if not EMAIL_RE.match(form["email"]):
            errors["email"] = "Please enter a valid email address."
        elif form["email"] != current_user.email and db.session.scalar(
            select(User).filter_by(email=form["email"])
        ):
            errors["email"] = "An account with this email already exists."
        if not errors:
            current_user.name = form["name"]
            current_user.email = form["email"]
            db.session.commit()
            flash("Your profile was updated.", "success")
            return redirect(url_for("account.profile"))
    status = 422 if errors else 200
    return render_template("account/profile.html", form=form, errors=errors), status
