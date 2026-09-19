"""Survey editor: pages, questions and choices.

Every mutating endpoint answers htmx requests with the re-rendered fragment and
plain form posts with a redirect back to the editor, so the editor keeps
working without JavaScript.
"""

import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .domain import sharing
from .domain.answers import parse_page
from .domain.branching import prune_invalid_rules, unreachable_pages, valid_targets
from .domain.ordering import choice_order
from .domain.question_form import PROMPT_MAX, parse_bulk_choices, parse_question_form
from .domain.question_types import default_settings, get_type
from .domain.results import completed_response_count
from .extensions import db
from .models import BranchRule, Choice, Page, Question, Survey
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


def drop_broken_rules(survey: Survey) -> None:
    db.session.flush()
    db.session.expire(survey, ["pages"])
    removed = prune_invalid_rules(survey)
    if removed:
        flash(
            f"Removed {removed} skip rule{'s' if removed > 1 else ''} that pointed to an "
            "earlier page.",
            "error",
        )


def renumber(items) -> None:
    for position, item in enumerate(items):
        item.position = position


@bp.get("/edit")
def edit(survey_id: int):
    survey = get_owned_survey(survey_id, with_tree=True)
    return render_template(
        "editor/edit.html",
        survey=survey,
        closed_reason=sharing.closed_reason(survey),
        completed=completed_response_count(survey),
        unreachable={page.id for page in unreachable_pages(survey)},
    )


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
    if "description" in request.form:
        page.description = request.form.get("description", "").strip()[:2000]
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


@bp.post("/pages/<int:page_id>/move")
def move_page(survey_id: int, page_id: int):
    survey = get_owned_survey(survey_id)
    page = get_page(survey, page_id)
    direction = request.form.get("direction")
    if direction not in ("up", "down"):
        abort(400)
    pages = list(survey.pages)
    index = pages.index(page)
    target = index - 1 if direction == "up" else index + 1
    if 0 <= target < len(pages):
        pages[index], pages[target] = pages[target], pages[index]
        renumber(pages)
        drop_broken_rules(survey)
        db.session.commit()
    if is_htmx():
        return "", 204, {"HX-Refresh": "true"}
    return back_to_editor(survey, f"page-{page.id}")


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


def render_question(survey: Survey, question: Question, errors=None, status=200):
    html = render_template(
        "editor/_question.html", survey=survey, question=question, errors=errors or {}
    )
    return html, status


@bp.post("/questions/<int:question_id>")
def update_question(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    changes, errors = parse_question_form(question, request.form)
    if errors:
        db.session.rollback()
        if is_htmx():
            return render_question(survey, question, errors, 422)
        flash(next(iter(errors.values())), "error")
        return back_to_editor(survey, f"question-{question.id}")

    changes.apply(question)
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


@bp.post("/questions/<int:question_id>/choices/bulk")
def add_choices_in_bulk(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    if not get_type(question.type).has_choices:
        abort(400)
    labels, error = parse_bulk_choices(
        request.form.get("options", ""), [c.label for c in question.choices]
    )
    if error:
        return render_question(survey, question, {"choices": error}, 422)
    for label in labels:
        question.choices.append(Choice(label=label, position=len(question.choices)))
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


@bp.post("/questions/<int:question_id>/duplicate")
def duplicate_question(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    page = question.page
    clone = Question(
        type=question.type,
        prompt=f"{question.prompt} (copy)"[:PROMPT_MAX],
        help_text=question.help_text,
        required=question.required,
        settings=dict(question.settings or {}),
    )
    clone.choices = [Choice(label=c.label, position=c.position) for c in question.choices]
    questions = list(page.questions)
    questions.insert(questions.index(question) + 1, clone)
    page.questions = questions
    renumber(questions)
    db.session.commit()
    if is_htmx():
        return render_template("editor/_page.html", survey=survey, page=page)
    return back_to_editor(survey, f"question-{clone.id}")


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


@bp.post("/questions/<int:question_id>/page")
def move_question_to_page(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    target = get_page(survey, request.form.get("page_id", type=int) or 0)
    source = question.page
    if target.id != source.id:
        question.position = len(target.questions)
        question.page = target  # moves it between the two collections
        renumber(source.questions)
        drop_broken_rules(survey)
        db.session.commit()
    if is_htmx():
        # Two pages changed; simplest is to let htmx reload the editor.
        return "", 204, {"HX-Refresh": "true"}
    return back_to_editor(survey, f"question-{question.id}")


@bp.route("/preview", methods=["GET", "POST"])
def preview(survey_id: int):
    """Walk through the survey like a respondent would, without saving anything."""
    survey = get_owned_survey(survey_id)
    index = request.args.get("page", 1, type=int) - 1
    index = min(max(index, 0), len(survey.pages) - 1)
    page = survey.pages[index]
    values, errors = {}, {}
    if request.method == "POST":
        _, errors = parse_page(page.questions, request.form)
        if not errors:
            if index + 1 < len(survey.pages):
                return redirect(url_for("editor.preview", survey_id=survey.id, page=index + 2))
            flash("That was the last page. Nothing was saved in preview mode.", "success")
            return back_to_editor(survey)
        values = {q.id: request.form.getlist(f"q{q.id}") for q in page.questions}
    return render_template(
        "public/page.html",
        survey=survey,
        page=page,
        page_number=index + 1,
        values=values,
        errors=errors,
        preview=True,
        # A fresh order each time, so the owner sees what shuffling does.
        choice_order=choice_order(page, secrets.token_hex(4)),
    ), (422 if errors else 200)


@bp.post("/questions/<int:question_id>/rules")
def add_rule(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = get_question(survey, question_id)
    if not get_type(question.type).has_choices:
        abort(400)
    choice = next(
        (c for c in question.choices if c.id == request.form.get("choice_id", type=int)), None
    )
    raw_target = request.form.get("target", "")
    target = None
    if raw_target != "end":
        targets = {p.id: p for p in valid_targets(survey, question.page)}
        target = targets.get(int(raw_target)) if raw_target.isdigit() else None
    if choice is None or (raw_target != "end" and target is None):
        return render_question(survey, question, {"rules": "Pick an option and a later page."}, 422)

    existing = next((r for r in question.branch_rules if r.choice_id == choice.id), None)
    if existing:
        existing.target_page = target
    else:
        question.branch_rules.append(BranchRule(choice=choice, target_page=target))
    db.session.commit()
    if is_htmx():
        return render_question(survey, question)
    return back_to_editor(survey, f"question-{question.id}")


@bp.post("/rules/<int:rule_id>/delete")
def delete_rule(survey_id: int, rule_id: int):
    survey = get_owned_survey(survey_id)
    rule = db.session.get(BranchRule, rule_id)
    if rule is None or rule.question.page.survey_id != survey.id:
        abort(404)
    question = rule.question
    question.branch_rules.remove(rule)
    db.session.commit()
    if is_htmx():
        return render_question(survey, question)
    return back_to_editor(survey, f"question-{question.id}")
