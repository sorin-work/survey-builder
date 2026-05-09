"""A small read-only JSON API for the signed-in owner (session cookie auth)."""

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user
from sqlalchemy import select

from .domain.results import ResponseFilter, completed_response_count, funnel, summarize
from .extensions import csrf, db
from .models import Survey

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


@bp.get("/surveys/<int:survey_id>/summary")
def summary(survey_id: int):
    survey = db.session.get(Survey, survey_id)
    if survey is None or survey.owner_id != current_user.id:
        abort(404)
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
