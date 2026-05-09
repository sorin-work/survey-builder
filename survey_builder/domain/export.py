"""CSV export of completed responses: one row per response, one column per question."""

import csv
import io
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Answer, Response
from .results import ALL_TIME, ResponseFilter, completed_filter

MULTI_SEPARATOR = "; "


def _cell(question, answers: list[Answer]) -> str:
    if not answers:
        return ""
    if question.type in ("single_choice", "multiple_choice"):
        labels = {c.id: c.label for c in question.choices}
        return MULTI_SEPARATOR.join(labels.get(a.choice_id, "") for a in answers)
    answer = answers[0]
    if answer.number_value is not None:
        return str(answer.number_value)
    if answer.date_value is not None:
        return answer.date_value.isoformat()
    return answer.text_value or ""


def export_rows(survey, period: ResponseFilter = ALL_TIME):
    # Same order as respondents see them: page by page, top to bottom.
    questions = survey.questions
    yield ["response_id", "submitted_at", *(q.prompt for q in questions)]

    responses = db.session.scalars(
        select(Response)
        .where(*completed_filter(survey, period))
        .order_by(Response.completed_at, Response.id)
        .options(selectinload(Response.answers))
    )
    for response in responses:
        by_question: dict[int, list[Answer]] = defaultdict(list)
        for answer in response.answers:
            by_question[answer.question_id].append(answer)
        yield [
            str(response.id),
            response.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
            *(_cell(q, by_question[q.id]) for q in questions),
        ]


def to_csv(survey, period: ResponseFilter = ALL_TIME) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(export_rows(survey, period))
    return buffer.getvalue()
