"""Owner-facing results: summaries, individual responses and exports."""

from flask import Blueprint, render_template
from flask_login import login_required

from .domain.results import completed_response_count, summarize
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
