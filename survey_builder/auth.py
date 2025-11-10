import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user
from sqlalchemy import select

from .extensions import db, login_manager
from .models import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_registration(name: str, email: str, password: str) -> dict[str, str]:
    errors = {}
    if not name.strip():
        errors["name"] = "Please enter your name."
    elif len(name.strip()) > 120:
        errors["name"] = "Name must be at most 120 characters."
    if not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return errors


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    errors: dict[str, str] = {}
    form = {"name": "", "email": ""}
    if request.method == "POST":
        form = {
            "name": request.form.get("name", ""),
            "email": normalize_email(request.form.get("email", "")),
        }
        password = request.form.get("password", "")
        errors = validate_registration(form["name"], form["email"], password)
        if not errors and db.session.scalar(select(User).filter_by(email=form["email"])):
            errors["email"] = "An account with this email already exists."
        if not errors:
            user = User(email=form["email"], name=form["name"].strip())
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Your account is ready.", "success")
            return redirect(url_for("index"))

    status = 422 if errors else 200
    return render_template("auth/register.html", form=form, errors=errors), status
