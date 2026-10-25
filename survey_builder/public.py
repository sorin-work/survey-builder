"""The public side: anonymous respondents filling in a shared survey.

Progress through a survey lives in the signed session cookie under
``survey:<token>``: the response key, the page the respondent is on, the pages
visited so far (for Back), drafts typed before going Back and the seed used to
shuffle options. The response row itself is created when the first page is
submitted, so people who only open the link do not show up as abandoned
responses.
"""

import secrets

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .domain import sharing
from .domain.answers import parse_page
from .domain.branching import next_page
from .domain.ordering import choice_order
from .extensions import db
from .models import Answer, Page, Response, Survey, utcnow

bp = Blueprint("public", __name__, url_prefix="/s")


@bp.before_request
def _allow_embedding():
    # Public surveys may be shown in an <iframe> on the owner's website.
    g.allow_framing = True
    g.embed = request.args.get("embed") == "1" or session.get("embed") is True
    if request.args.get("embed") == "1":
        session["embed"] = True


def get_survey_by_token(token: str) -> Survey:
    survey = db.session.scalar(select(Survey).filter_by(share_token=token))
    if survey is None or survey.status == sharing.DRAFT:
        abort(404)
    return survey


def closed_page(survey: Survey):
    """The "no longer accepting responses" page, or None while the survey is open."""
    reason = sharing.closed_reason(survey)
    if reason is None:
        return None
    return render_template("public/closed.html", survey=survey, reason=reason), 410


def session_key(survey: Survey) -> str:
    return f"survey:{survey.share_token}"


def load_state(survey: Survey) -> dict:
    return dict(session.get(session_key(survey), {}))


def save_state(survey: Survey, state: dict) -> None:
    # Keep the cookie across browser restarts so people can finish later.
    session.permanent = True
    session[session_key(survey)] = state


def find_response(survey: Survey, state: dict) -> Response | None:
    key = state.get("key")
    if not key:
        return None
    return db.session.scalar(select(Response).filter_by(survey_id=survey.id, key=key))


def current_page(survey: Survey, state: dict) -> Page:
    page_id = state.get("page_id")
    for page in survey.pages:
        if page.id == page_id:
            return page
    return survey.pages[0]


def store_answers(response: Response, page: Page, parsed) -> None:
    """Save the answers for one page, replacing any given earlier (after Back)."""
    page_questions = {q.id for q in page.questions}
    for existing in [a for a in response.answers if a.question_id in page_questions]:
        response.answers.remove(existing)
    for answer in parsed:
        if answer.is_empty:
            continue
        if answer.choice_ids:
            for choice_id in answer.choice_ids:
                response.answers.append(Answer(question_id=answer.question_id, choice_id=choice_id))
        else:
            response.answers.append(
                Answer(
                    question_id=answer.question_id,
                    text_value=answer.text,
                    number_value=answer.number,
                    date_value=answer.day,
                )
            )


def drop_skipped_answers(survey: Survey, response: Response, visited: set[int]) -> None:
    """Forget answers to pages the respondent did not pass through in the end.

    Someone can answer page 2, go back and change an answer so that a skip
    rule now jumps over page 2; those answers must not count.
    """
    on_path = {q.id for p in survey.pages if p.id in visited for q in p.questions}
    for answer in [a for a in response.answers if a.question_id not in on_path]:
        response.answers.remove(answer)


def saved_values(response: Response | None, page: Page) -> dict[int, list[str]]:
    """Answers already stored for a page, in the shape the form fields expect."""
    if response is None:
        return {}
    question_ids = {q.id for q in page.questions}
    values: dict[int, list[str]] = {}
    for answer in response.answers:
        if answer.question_id not in question_ids:
            continue
        if answer.choice_id is not None:
            raw = str(answer.choice_id)
        elif answer.number_value is not None:
            raw = str(answer.number_value)
        elif answer.date_value is not None:
            raw = answer.date_value.isoformat()
        else:
            raw = answer.text_value or ""
        values.setdefault(answer.question_id, []).append(raw)
    return values


def render_page(
    survey: Survey, page: Page, values=None, errors=None, status=200, can_go_back=False
):
    state = load_state(survey)
    if "seed" not in state or "key" not in state:
        state.setdefault("seed", secrets.token_hex(8))
        # The response key is fixed before the first submit, so a double
        # click sends the same key twice instead of starting two responses.
        state.setdefault("key", secrets.token_hex(16))
        save_state(survey, state)
    html = render_template(
        "public/page.html",
        survey=survey,
        page=page,
        page_number=survey.pages.index(page) + 1,
        values=values or {},
        errors=errors or {},
        can_go_back=can_go_back,
        choice_order=choice_order(page, state["seed"]),
    )
    return html, status


@bp.get("/<token>")
def show(token: str):
    survey = get_survey_by_token(token)
    if closed := closed_page(survey):
        return closed
    state = load_state(survey)
    if state.get("done"):
        return redirect(url_for("public.thanks", token=token))
    page = current_page(survey, state)
    values = saved_values(find_response(survey, state), page)
    draft = state.get("drafts", {}).get(str(page.id))
    if draft:
        values = {int(qid): raw for qid, raw in draft.items()}
    return render_page(survey, page, values, can_go_back=bool(state.get("history")))


@bp.post("/<token>")
def submit(token: str):
    survey = get_survey_by_token(token)
    if closed := closed_page(survey):
        return closed
    state = load_state(survey)
    if state.get("done"):
        return redirect(url_for("public.thanks", token=token))

    page = current_page(survey, state)
    if request.form.get("page_id") != str(page.id):
        # A stale form (another tab, browser back button): show the current page.
        return redirect(url_for("public.show", token=token))

    parsed, errors = parse_page(page.questions, request.form)
    if errors:
        values = {q.id: request.form.getlist(f"q{q.id}") for q in page.questions}
        return render_page(
            survey, page, values, errors, status=422, can_go_back=bool(state.get("history"))
        )

    response = find_response(survey, state)
    if response is None:
        state.setdefault("key", secrets.token_hex(16))
        response = Response(survey=survey, key=state["key"])
        db.session.add(response)
    store_answers(response, page, parsed)
    state.get("drafts", {}).pop(str(page.id), None)

    following = next_page(survey, page, parsed)
    if following is None:
        drop_skipped_answers(survey, response, {*state.get("history", []), page.id})
        response.completed_at = utcnow()
        state["done"] = True
    else:
        state["page_id"] = following.id
        state["history"] = [*state.get("history", []), page.id]
    try:
        db.session.commit()
    except IntegrityError:
        # The same submission is being saved by a parallel request.
        db.session.rollback()
        return redirect(url_for("public.show", token=token))
    save_state(survey, state)

    if state.get("done"):
        return redirect(url_for("public.thanks", token=token))
    return redirect(url_for("public.show", token=token))


@bp.post("/<token>/back")
def back(token: str):
    survey = get_survey_by_token(token)
    state = load_state(survey)
    history = list(state.get("history", []))
    if history and not state.get("done"):
        # Keep what was typed on this page (valid or not) for when they return.
        page = current_page(survey, state)
        drafts = dict(state.get("drafts", {}))
        drafts[str(page.id)] = {str(q.id): request.form.getlist(f"q{q.id}") for q in page.questions}
        state["drafts"] = drafts
        state["page_id"] = history.pop()
        state["history"] = history
        save_state(survey, state)
    return redirect(url_for("public.show", token=token))


@bp.post("/<token>/again")
def again(token: str):
    """Kiosk mode: forget the finished response so the next person can start."""
    survey = get_survey_by_token(token)
    if not survey.allow_multiple:
        abort(404)
    session.pop(session_key(survey), None)
    return redirect(url_for("public.show", token=token))


@bp.get("/<token>/thanks")
def thanks(token: str):
    survey = get_survey_by_token(token)
    return render_template("public/thanks.html", survey=survey)
