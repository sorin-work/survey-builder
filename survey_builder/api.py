"""A small read-only JSON API for the signed-in owner (session cookie auth)."""

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .domain.pagination import Pagination
from .domain.results import (
    ResponseFilter,
    completed_filter,
    completed_response_count,
    funnel,
    summarize,
)
from .extensions import csrf, db
from .models import Answer, Response, Survey

bp = Blueprint("api", __name__, url_prefix="/api")
csrf.exempt(bp)


@bp.before_request
def _require_login():
    if not current_user.is_authenticated:
        return jsonify(error="authentication required"), 401


@bp.errorhandler(404)
def _not_found(_error):
    return jsonify(error="not found"), 404


def survey_json(survey: Survey) -> dict:
    return {
        "id": survey.id,
        "title": survey.title,
        "status": survey.status,
        "share_token": survey.share_token,
        "closes_on": survey.closes_on.isoformat() if survey.closes_on else None,
        "response_limit": survey.response_limit,
        "created_at": survey.created_at.isoformat() + "Z",
    }


@bp.get("/surveys")
def list_surveys():
    surveys = db.session.scalars(
        select(Survey).filter_by(owner_id=current_user.id).order_by(Survey.id)
    ).all()
    return jsonify(surveys=[survey_json(s) for s in surveys])


def owned_survey(survey_id: int) -> Survey:
    survey = db.session.get(Survey, survey_id)
    if survey is None or survey.owner_id != current_user.id:
        abort(404)
    return survey


def answer_value(question, answers):
    if not answers:
        return None
    if question.type == "multiple_choice":
        return [a.choice.label for a in answers]
    answer = answers[0]
    if answer.choice_id is not None:
        return answer.choice.label
    if answer.number_value is not None:
        return answer.number_value
    if answer.date_value is not None:
        return answer.date_value.isoformat()
    return answer.text_value


@bp.get("/surveys/<int:survey_id>/responses")
def responses(survey_id: int):
    survey = owned_survey(survey_id)
    period = ResponseFilter.from_args(request.args)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)
    pagination = Pagination.from_request(
        request.args.get("page"), completed_response_count(survey, period), per_page=per_page
    )
    rows = db.session.scalars(
        select(Response)
        .where(*completed_filter(survey, period))
        .order_by(Response.completed_at, Response.id)
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .options(selectinload(Response.answers).selectinload(Answer.choice))
    ).all()
    questions = survey.questions
    items = []
    for response in rows:
        by_question = {}
        for answer in response.answers:
            by_question.setdefault(answer.question_id, []).append(answer)
        items.append(
            {
                "id": response.id,
                "completed_at": response.completed_at.isoformat() + "Z",
                "answers": {str(q.id): answer_value(q, by_question.get(q.id)) for q in questions},
            }
        )
    return jsonify(
        responses=items,
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )


@bp.get("/surveys/<int:survey_id>/summary")
def summary(survey_id: int):
    survey = owned_survey(survey_id)
    period = ResponseFilter.from_args(request.args)
    stats = funnel(survey, period)
    questions = []
    for item in summarize(survey, period):
        question = item.question
        entry = {
            "id": question.id,
            "type": question.type,
            "prompt": question.prompt,
            "answered": item.answered,
        }
        if item.labels:
            entry["labels"] = item.labels
            entry["counts"] = item.counts
        if item.average is not None:
            entry["average"] = item.average
            entry["median"] = item.median
        if item.nps is not None:
            entry["nps"] = {
                "score": item.nps.score,
                "promoters": item.nps.promoters,
                "passives": item.nps.passives,
                "detractors": item.nps.detractors,
            }
        questions.append(entry)
    return jsonify(
        survey=survey_json(survey),
        responses={
            "completed": completed_response_count(survey, period),
            "started": stats.started,
            "completion_rate": stats.completion_rate,
            "median_seconds": stats.median_seconds,
        },
        questions=questions,
    )
