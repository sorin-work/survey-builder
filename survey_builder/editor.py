"""Survey editor: pages, questions and choices.

Every mutating endpoint answers htmx requests with the re-rendered fragment and
plain form posts with a redirect back to the editor, so the editor keeps
working without JavaScript.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .domain.question_types import default_settings, get_type
from .domain.settings import parse_settings
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
    return render_template("editor/edit.html", survey=survey)


@bp.post("/pages")
def add_page(survey_id: int):
    survey = get_owned_survey(survey_id)
    page = Page(title=request.form.get("title", "").strip()[:200], position=len(survey.pages))
    survey.pages.append(page)
    db.session.commit()
    if is_htmx():
        return render_template("editor/_page.html", survey=survey, page=page)
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


PROMPT_MAX = 500
HELP_MAX = 500
CHOICE_MAX = 300


def render_question(survey: Survey, question: Question, errors=None, status=200):
    html = render_template(
        "editor/_question.html", survey=survey, question=question, errors=errors or {}
    )
    return html, status


@bp.post("/questions/<int:question_id>")
def update_question(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    prompt = request.form.get("prompt", "").strip()
    help_text = request.form.get("help_text", "").strip()
    errors = {}
    if not prompt:
        errors["prompt"] = "The question needs some text."
    elif len(prompt) > PROMPT_MAX:
        errors["prompt"] = f"Keep the question under {PROMPT_MAX} characters."
    if len(help_text) > HELP_MAX:
        errors["help_text"] = f"Keep the help text under {HELP_MAX} characters."
    settings, setting_errors = parse_settings(question.type, request.form)
    errors.update(setting_errors)
    labels = {}
    for choice in question.choices:
        label = request.form.get(f"choice_{choice.id}")
        if label is None:
            continue
        label = label.strip()
        if not label:
            errors["choices"] = "Options cannot be empty."
        elif len(label) > CHOICE_MAX:
            errors["choices"] = f"Keep options under {CHOICE_MAX} characters."
        labels[choice] = label
    if "choices" not in errors and len(set(labels.values())) < len(labels):
        errors["choices"] = "Each option must be different."

    if errors:
        db.session.rollback()
        if is_htmx():
            return render_question(survey, question, errors, 422)
        flash(next(iter(errors.values())), "error")
        return back_to_editor(survey, f"question-{question.id}")

    question.prompt = prompt
    question.help_text = help_text
    question.required = request.form.get("required") == "on"
    question.settings = settings
    for choice, label in labels.items():
        choice.label = label
    db.session.commit()
    if is_htmx():
        return render_question(survey, question)
    return back_to_editor(survey, f"question-{question.id}")


def get_choice(survey: Survey, choice_id: int) -> Choice:
    choice = db.session.get(Choice, choice_id)
    if choice is None or choice.question.page.survey_id != survey.id:
        abort(404)
    return choice


@bp.post("/questions/<int:question_id>/choices")
def add_choice(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    if not get_type(question.type).has_choices:
        abort(400)
    number = len(question.choices) + 1
    question.choices.append(Choice(label=f"Option {number}", position=number - 1))
    db.session.commit()
    if is_htmx():
        return render_question(survey, question)
    return back_to_editor(survey, f"question-{question.id}")


@bp.post("/choices/<int:choice_id>/delete")
def delete_choice(survey_id: int, choice_id: int):
    survey = get_owned_survey(survey_id)
    choice = get_choice(survey, choice_id)
    question = choice.question
    if len(question.choices) <= 1:
        if is_htmx():
            return render_question(survey, question, {"choices": "Keep at least one option."}, 422)
        flash("Keep at least one option.", "error")
        return back_to_editor(survey, f"question-{question.id}")
    question.choices.remove(choice)
    renumber(question.choices)
    db.session.commit()
    if is_htmx():
        return render_question(survey, question)
    return back_to_editor(survey, f"question-{question.id}")


@bp.post("/questions/<int:question_id>/delete")
def delete_question(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    page = question.page
    page.questions.remove(question)
    renumber(page.questions)
    db.session.commit()
    if is_htmx():
        return ""
    return back_to_editor(survey, f"page-{page.id}")


@bp.post("/questions/<int:question_id>/move")
def move_question(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    page = question.page
    direction = request.form.get("direction")
    if direction not in ("up", "down"):
        abort(400)
    questions = list(page.questions)
    index = questions.index(question)
    target = index - 1 if direction == "up" else index + 1
    if 0 <= target < len(questions):
        questions[index], questions[target] = questions[target], questions[index]
        renumber(questions)
        db.session.commit()
        db.session.refresh(page)
    if is_htmx():
        return render_template("editor/_page.html", survey=survey, page=page)
    return back_to_editor(survey, f"question-{question.id}")
