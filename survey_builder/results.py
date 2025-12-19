"""Owner-facing results: summaries, individual responses and exports."""

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import select

from .domain.pagination import Pagination
from .domain.results import completed_response_count, summarize
from .extensions import db
from .models import Response
from .surveys import get_owned_survey

bp = Blueprint("results", __name__, url_prefix="/surveys/<int:survey_id>/results")


@bp.before_request
@login_required
def _require_login():
    pass


@bp.get("/")
def summary(survey_id: int):
    survey = get_owned_survey(survey_id)
    return render_template(
        "results/summary.html",
        survey=survey,
        total=completed_response_count(survey),
        summaries=summarize(survey),
    )


@bp.get("/responses")
def responses(survey_id: int):
    survey = get_owned_survey(survey_id)
    pagination = Pagination.from_request(
        request.args.get("page"), completed_response_count(survey), per_page=25
    )
    rows = db.session.scalars(
        select(Response)
        .where(Response.survey_id == survey.id, Response.completed_at.is_not(None))
        .order_by(Response.completed_at.desc(), Response.id.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
    ).all()
    return render_template(
        "results/responses.html", survey=survey, responses=rows, pagination=pagination
    )
