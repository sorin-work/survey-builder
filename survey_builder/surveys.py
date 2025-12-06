from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from .domain import sharing
from .extensions import db
from .models import Page, Survey, utcnow

bp = Blueprint("surveys", __name__, url_prefix="/surveys")

TITLE_MAX = 200


@bp.before_request
@login_required
def _require_login():
    pass


def get_owned_survey(survey_id: int) -> Survey:
    survey = db.session.get(Survey, survey_id)
    if survey is None or survey.owner_id != current_user.id:
        abort(404)
    return survey


THANK_YOU_MAX = 2000


def validate_survey_form(title: str, thank_you: str = "") -> dict[str, str]:
    errors = {}
    if not title:
        errors["title"] = "Give your survey a title."
    elif len(title) > TITLE_MAX:
        errors["title"] = f"Title must be at most {TITLE_MAX} characters."
    if len(thank_you) > THANK_YOU_MAX:
        errors["thank_you_message"] = f"Keep the message under {THANK_YOU_MAX} characters."
    return errors


@bp.get("/")
def dashboard():
    surveys = db.session.scalars(
        select(Survey).filter_by(owner_id=current_user.id).order_by(Survey.updated_at.desc())
    ).all()
    return render_template("surveys/dashboard.html", surveys=surveys)


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = {"title": "", "description": ""}
    errors: dict[str, str] = {}
    if request.method == "POST":
        form = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
        }
        errors = validate_survey_form(form["title"])
        if not errors:
            survey = Survey(owner_id=current_user.id, **form)
            survey.pages.append(Page(title="", position=0))
            db.session.add(survey)
            db.session.commit()
            flash("Survey created. Add your first questions below.", "success")
            return redirect(url_for("editor.edit", survey_id=survey.id))
    status = 422 if errors else 200
    return render_template("surveys/form.html", form=form, errors=errors, survey=None), status


@bp.route("/<int:survey_id>/settings", methods=["GET", "POST"])
def edit(survey_id: int):
    survey = get_owned_survey(survey_id)
    form = {
        "title": survey.title,
        "description": survey.description,
        "thank_you_message": survey.thank_you_message,
    }
    errors: dict[str, str] = {}
    if request.method == "POST":
        form = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "thank_you_message": request.form.get("thank_you_message", "").strip(),
        }
        errors = validate_survey_form(form["title"], form["thank_you_message"])
        if not errors:
            survey.title = form["title"]
            survey.description = form["description"]
            survey.thank_you_message = form["thank_you_message"]
            db.session.commit()
            flash("Survey updated.", "success")
            return redirect(url_for("surveys.dashboard"))
    status = 422 if errors else 200
    return render_template("surveys/form.html", form=form, errors=errors, survey=survey), status


@bp.post("/<int:survey_id>/delete")
def delete(survey_id: int):
    survey = get_owned_survey(survey_id)
    db.session.delete(survey)
    db.session.commit()
    flash(f"Deleted “{survey.title}”.", "success")
    return redirect(url_for("surveys.dashboard"))


@bp.post("/<int:survey_id>/publish")
def publish(survey_id: int):
    survey = get_owned_survey(survey_id)
    problems = sharing.publish_problems(survey)
    if problems:
        for problem in problems:
            flash(problem, "error")
        return redirect(url_for("editor.edit", survey_id=survey.id))
    if survey.share_token is None:
        survey.share_token = sharing.new_share_token()
    survey.status = sharing.PUBLISHED
    survey.published_at = survey.published_at or utcnow()
    db.session.commit()
    flash("Your survey is live. Share the link below.", "success")
    return redirect(url_for("editor.edit", survey_id=survey.id))


@bp.post("/<int:survey_id>/close")
def close(survey_id: int):
    survey = get_owned_survey(survey_id)
    if survey.status == sharing.PUBLISHED:
        survey.status = sharing.CLOSED
        db.session.commit()
        flash("The survey no longer accepts responses.", "success")
    return redirect(url_for("editor.edit", survey_id=survey.id))
