"""Owner-facing results: summaries, individual responses and exports."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask import (
    Response as HttpResponse,
)
from flask_login import login_required
from sqlalchemy import select

from .domain.export import to_csv
from .domain.pagination import Pagination
from .domain.results import Period, completed_response_count, summarize
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
    period = Period.from_args(request.args)
    return render_template(
        "results/summary.html",
        survey=survey,
        period=period,
        total=completed_response_count(survey, period),
        summaries=summarize(survey, period),
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


@bp.get("/responses/<int:response_id>")
def response_detail(survey_id: int, response_id: int):
    survey = get_owned_survey(survey_id)
    response = db.session.get(Response, response_id)
    if response is None:
        abort(404)
    by_question: dict[int, list] = {}
    for answer in response.answers:
        by_question.setdefault(answer.question_id, []).append(answer)
    return render_template(
        "results/response.html", survey=survey, response=response, by_question=by_question
    )


@bp.post("/responses/<int:response_id>/delete")
def delete_response(survey_id: int, response_id: int):
    survey = get_owned_survey(survey_id)
    response = db.session.get(Response, response_id)
    if response is None or response.survey_id != survey.id:
        abort(404)
    db.session.delete(response)
    db.session.commit()
    flash(f"Response #{response_id} deleted.", "success")
    return redirect(url_for("results.responses", survey_id=survey.id))


def export_filename(survey) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in survey.title.lower()).strip("-")
    return f"{safe or 'survey'}-responses.csv"


@bp.get("/export.csv")
def export_csv(survey_id: int):
    survey = get_owned_survey(survey_id)
    return HttpResponse(
        to_csv(survey),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{export_filename(survey)}"'},
    )
