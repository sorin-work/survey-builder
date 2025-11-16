"""Survey editor: pages, questions and choices.

Every mutating endpoint answers htmx requests with the re-rendered fragment and
plain form posts with a redirect back to the editor, so the editor keeps
working without JavaScript.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .domain.question_types import QUESTION_TYPES, default_settings, get_type
from .extensions import db
from .models import Choice, Page, Question, Survey
from .surveys import get_owned_survey

bp = Blueprint("editor", __name__, url_prefix="/surveys/<int:survey_id>")


@bp.before_request
@login_required
def _require_login():
    pass


def is_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def back_to_editor(survey: Survey, anchor: str = ""):
    return redirect(url_for("editor.edit", survey_id=survey.id) + (f"#{anchor}" if anchor else ""))


def get_page(survey: Survey, page_id: int) -> Page:
    page = db.session.get(Page, page_id)
    if page is None or page.survey_id != survey.id:
        abort(404)
    return page


def get_question(survey: Survey, question_id: int) -> Question:
    question = db.session.get(Question, question_id)
    if question is None or question.page.survey_id != survey.id:
        abort(404)
    return question


def renumber(items) -> None:
    for position, item in enumerate(items):
        item.position = position


@bp.get("/edit")
def edit(survey_id: int):
    survey = get_owned_survey(survey_id)
    return render_template("editor/edit.html", survey=survey, question_types=QUESTION_TYPES)


@bp.post("/pages")
def add_page(survey_id: int):
    survey = get_owned_survey(survey_id)
    page = Page(title=request.form.get("title", "").strip()[:200], position=len(survey.pages))
    survey.pages.append(page)
    db.session.commit()
    if is_htmx():
        return render_template(
            "editor/_page.html", survey=survey, page=page, question_types=QUESTION_TYPES
        )
    return back_to_editor(survey, f"page-{page.id}")


@bp.post("/pages/<int:page_id>")
def rename_page(survey_id: int, page_id: int):
    survey = get_owned_survey(survey_id)
    page = get_page(survey, page_id)
    page.title = request.form.get("title", "").strip()[:200]
    db.session.commit()
    if is_htmx():
        return render_template("editor/_page_title.html", survey=survey, page=page)
    return back_to_editor(survey, f"page-{page.id}")


@bp.post("/pages/<int:page_id>/delete")
def delete_page(survey_id: int, page_id: int):
    survey = get_owned_survey(survey_id)
    page = get_page(survey, page_id)
    if len(survey.pages) == 1:
        flash("A survey needs at least one page.", "error")
        return back_to_editor(survey)
    survey.pages.remove(page)
    renumber(survey.pages)
    db.session.commit()
    if is_htmx():
        return ""
    return back_to_editor(survey)


@bp.post("/pages/<int:page_id>/questions")
def add_question(survey_id: int, page_id: int):
    survey = get_owned_survey(survey_id)
    page = get_page(survey, page_id)
    try:
        qtype = get_type(request.form.get("type", ""))
    except ValueError:
        abort(400)
    question = Question(
        type=qtype.key,
        prompt="Untitled question",
        position=len(page.questions),
        settings=default_settings(qtype.key),
    )
    if qtype.has_choices:
        question.choices = [Choice(label=f"Option {i}", position=i - 1) for i in (1, 2)]
    page.questions.append(question)
    db.session.commit()
    if is_htmx():
        return render_template("editor/_question.html", survey=survey, question=question)
    return back_to_editor(survey, f"question-{question.id}")
