"""The public side: anonymous respondents filling in a shared survey."""

from flask import Blueprint, abort, render_template
from sqlalchemy import select

from .domain import sharing
from .extensions import db
from .models import Survey

bp = Blueprint("public", __name__, url_prefix="/s")


def get_survey_by_token(token: str) -> Survey:
    survey = db.session.scalar(select(Survey).filter_by(share_token=token))
    if survey is None or survey.status == sharing.DRAFT:
        abort(404)
    return survey


@bp.get("/<token>")
def show(token: str):
    survey = get_survey_by_token(token)
    if not sharing.is_accepting_responses(survey):
        return render_template("public/closed.html", survey=survey), 410
    page = survey.pages[0]
    return render_template(
        "public/page.html",
        survey=survey,
        page=page,
        page_number=1,
        values={},
        errors={},
    )
