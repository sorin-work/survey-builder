"""Owner-facing results: summaries, individual responses and exports."""

from flask import (
    Blueprint,
    Response as HttpResponse,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import delete, select

from .domain.export import to_csv
from .domain.pagination import Pagination
from .domain.results import (
    ResponseFilter,
    completed_response_count,
    daily_counts,
    funnel,
    nps_by_month,
    summarize,
)
from .extensions import db
from .models import Answer, Question, Response
from .surveys import get_owned_survey

bp = Blueprint("results", __name__, url_prefix="/surveys/<int:survey_id>/results")


@bp.before_request
@login_required
def _require_login():
    pass


def get_survey_response(survey, response_id: int) -> Response:
    """A response of ``survey``; 404 for unknown ids and responses of other surveys."""
    response = db.session.get(Response, response_id)
    if response is None or response.survey_id != survey.id:
        abort(404)
    return response


def neighbours(survey, response) -> tuple[int | None, int | None]:
    """Ids of the next newer and next older completed response, as listed."""
    if response.completed_at is None:
        return None, None
    base = select(Response.id).where(
        Response.survey_id == survey.id, Response.completed_at.is_not(None)
    )
    key = (Response.completed_at, Response.id)
    newer = db.session.scalar(
        base.where(db.tuple_(*key) > db.tuple_(response.completed_at, response.id))
        .order_by(Response.completed_at, Response.id)
        .limit(1)
    )
    older = db.session.scalar(
        base.where(db.tuple_(*key) < db.tuple_(response.completed_at, response.id))
        .order_by(Response.completed_at.desc(), Response.id.desc())
        .limit(1)
    )
    return newer, older


@bp.get("/")
def summary(survey_id: int):
    survey = get_owned_survey(survey_id, with_tree=True)
    period = ResponseFilter.from_args(request.args)
    return render_template(
        "results/summary.html",
        survey=survey,
        period=period,
        total=completed_response_count(survey, period),
        summaries=summarize(survey, period),
        timeline=daily_counts(survey, period),
        funnel=funnel(survey, period),
        overall=({} if period.is_open else {item.question.id: item for item in summarize(survey)}),
        nps_trends={
            q.id: nps_by_month(survey, q, period) for q in survey.questions if q.type == "nps"
        },
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
    answered = dict(
        db.session.execute(
            select(Answer.response_id, db.func.count(db.distinct(Answer.question_id)))
            .where(Answer.response_id.in_([r.id for r in rows]))
            .group_by(Answer.response_id)
        ).all()
    )
    return render_template(
        "results/responses.html",
        survey=survey,
        responses=rows,
        answered=answered,
        pagination=pagination,
    )


@bp.get("/responses/<int:response_id>")
def response_detail(survey_id: int, response_id: int):
    survey = get_owned_survey(survey_id)
    response = get_survey_response(survey, response_id)
    by_question = response.answers_by_question()
    newer, older = neighbours(survey, response)
    return render_template(
        "results/response.html",
        survey=survey,
        response=response,
        by_question=by_question,
        newer=newer,
        older=older,
    )


@bp.post("/responses/<int:response_id>/delete")
def delete_response(survey_id: int, response_id: int):
    survey = get_owned_survey(survey_id)
    response = get_survey_response(survey, response_id)
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
    # The BOM makes Excel read the file as UTF-8 instead of the local code page.
    body = "\ufeff" + to_csv(survey, ResponseFilter.from_args(request.args))
    return HttpResponse(
        body.encode("utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{export_filename(survey)}"'},
    )


@bp.get("/questions/<int:question_id>")
def text_answers(survey_id: int, question_id: int):
    survey = get_owned_survey(survey_id)
    question = db.session.get(Question, question_id)
    if question is None or question.page.survey_id != survey.id:
        abort(404)
    if question.type not in ("short_text", "long_text"):
        abort(404)
    base = (
        select(Answer)
        .join(Response)
        .where(
            Answer.question_id == question.id,
            Answer.text_value.is_not(None),
            Response.completed_at.is_not(None),
        )
    )
    total = db.session.scalar(select(db.func.count()).select_from(base.subquery()))
    pagination = Pagination.from_request(request.args.get("page"), total, per_page=50)
    answers = db.session.scalars(
        base.order_by(Response.completed_at.desc(), Answer.id.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
    ).all()
    return render_template(
        "results/text_answers.html",
        survey=survey,
        question=question,
        answers=answers,
        pagination=pagination,
    )


@bp.post("/clear")
def clear_responses(survey_id: int):
    survey = get_owned_survey(survey_id)
    if request.form.get("confirm", "").strip() != survey.title:
        flash("Type the survey title exactly to delete all of its responses.", "error")
        return redirect(url_for("surveys.edit", survey_id=survey.id))
    removed = db.session.execute(delete(Response).where(Response.survey_id == survey.id))
    db.session.commit()
    flash(f"Deleted {removed.rowcount} responses.", "success")
    return redirect(url_for("results.summary", survey_id=survey.id))
