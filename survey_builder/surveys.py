from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .domain import sharing
from .domain.copying import copy_survey
from .domain.templates import TEMPLATES, build_from_template
from .extensions import db
from .models import Page, Question, Response, Survey, utcnow

bp = Blueprint("surveys", __name__, url_prefix="/surveys")

TITLE_MAX = 200


@bp.before_request
@login_required
def _require_login():
    pass


def get_owned_survey(survey_id: int, with_tree: bool = False) -> Survey:
    """The current user's survey or 404. ``with_tree`` loads pages, questions,
    choices and rules up front for pages that render all of them."""
    if with_tree:
        questions = selectinload(Survey.pages).selectinload(Page.questions)
        survey = db.session.scalar(
            select(Survey)
            .where(Survey.id == survey_id)
            .options(
                questions.selectinload(Question.choices),
                questions.selectinload(Question.branch_rules),
            )
        )
    else:
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


def parse_share_settings(form) -> tuple[dict, dict[str, str]]:
    values: dict = {"closes_on": None, "response_limit": None}
    errors: dict[str, str] = {}
    raw_date = form.get("closes_on", "").strip()
    if raw_date:
        try:
            values["closes_on"] = date.fromisoformat(raw_date)
        except ValueError:
            errors["closes_on"] = "Enter a date as YYYY-MM-DD."
    raw_limit = form.get("response_limit", "").strip()
    if raw_limit:
        try:
            values["response_limit"] = int(raw_limit)
        except ValueError:
            errors["response_limit"] = "Enter a whole number."
        else:
            if values["response_limit"] < 1:
                errors["response_limit"] = "The limit must be at least 1."
    return values, errors


SORTS = {
    "updated": ("Recently updated", Survey.updated_at.desc()),
    "created": ("Newest first", Survey.created_at.desc()),
    "title": ("Title A-Z", db.func.lower(Survey.title)),
}


@bp.get("/")
def dashboard():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    stmt = select(Survey).filter_by(owner_id=current_user.id)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Survey.title.ilike(f"%{escaped}%", escape="\\"))
    if status in (sharing.DRAFT, sharing.PUBLISHED, sharing.CLOSED):
        stmt = stmt.filter_by(status=status)
    sort = request.args.get("sort", "updated")
    if sort not in SORTS:
        sort = "updated"
    surveys = db.session.scalars(stmt.order_by(SORTS[sort][1], Survey.id.desc())).all()
    counts = dict(
        db.session.execute(
            select(Response.survey_id, db.func.count(Response.id))
            .join(Survey)
            .where(Survey.owner_id == current_user.id, Response.completed_at.is_not(None))
            .group_by(Response.survey_id)
        ).all()
    )
    return render_template(
        "surveys/dashboard.html",
        surveys=surveys,
        counts=counts,
        query=query,
        status=status,
        sort=sort,
        sorts={key: label for key, (label, _) in SORTS.items()},
        filtered=bool(query or status),
    )


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
    return render_template(
        "surveys/form.html", form=form, errors=errors, survey=None, templates=TEMPLATES
    ), status


@bp.post("/new/from-template")
def create_from_template():
    template = TEMPLATES.get(request.form.get("template", ""))
    if template is None:
        abort(400)
    survey = build_from_template(template, current_user.id)
    db.session.add(survey)
    db.session.commit()
    flash(f"Started from the \u201c{template.title}\u201d template.", "success")
    return redirect(url_for("editor.edit", survey_id=survey.id))


@bp.route("/<int:survey_id>/settings", methods=["GET", "POST"])
def edit(survey_id: int):
    survey = get_owned_survey(survey_id)
    form = {
        "title": survey.title,
        "description": survey.description,
        "thank_you_message": survey.thank_you_message,
        "closes_on": survey.closes_on.isoformat() if survey.closes_on else "",
        "response_limit": survey.response_limit or "",
        "allow_multiple": survey.allow_multiple,
    }
    errors: dict[str, str] = {}
    if request.method == "POST":
        form = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "thank_you_message": request.form.get("thank_you_message", "").strip(),
            "closes_on": request.form.get("closes_on", "").strip(),
            "response_limit": request.form.get("response_limit", "").strip(),
            "allow_multiple": request.form.get("allow_multiple") == "on",
        }
        errors = validate_survey_form(form["title"], form["thank_you_message"])
        share, share_errors = parse_share_settings(request.form)
        errors.update(share_errors)
        if not errors:
            survey.closes_on = share["closes_on"]
            survey.response_limit = share["response_limit"]
            survey.allow_multiple = form["allow_multiple"]
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


@bp.post("/<int:survey_id>/duplicate")
def duplicate(survey_id: int):
    survey = get_owned_survey(survey_id)
    clone = copy_survey(survey)
    db.session.add(clone)
    db.session.commit()
    flash(f"Created \u201c{clone.title}\u201d as a draft.", "success")
    return redirect(url_for("editor.edit", survey_id=clone.id))
