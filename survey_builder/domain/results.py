"""Aggregating completed responses into per-question summaries."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from ..extensions import db
from ..models import Answer, Response
from .question_types import DATE, LONG_TEXT, MULTIPLE_CHOICE, NPS, RATING, SHORT_TEXT, SINGLE_CHOICE

TEXT_SAMPLE_SIZE = 10


@dataclass
class QuestionSummary:
    question: object
    answered: int = 0
    # Chart data: parallel lists of labels and counts.
    labels: list[str] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)
    average: float | None = None
    texts: list[str] = field(default_factory=list)
    earliest: object = None
    latest: object = None

    @property
    def percentages(self) -> list[float]:
        if not self.answered:
            return [0.0 for _ in self.counts]
        return [round(100 * count / self.answered, 1) for count in self.counts]


def completed_response_count(survey) -> int:
    return db.session.scalar(
        select(db.func.count(Response.id)).where(
            Response.survey_id == survey.id, Response.completed_at.is_not(None)
        )
    )


def _answers_by_question(survey) -> dict[int, list[Answer]]:
    rows = db.session.scalars(
        select(Answer)
        .join(Response)
        .where(Response.survey_id == survey.id, Response.completed_at.is_not(None))
        .order_by(Response.completed_at.desc(), Answer.id)
    )
    grouped: dict[int, list[Answer]] = defaultdict(list)
    for answer in rows:
        grouped[answer.question_id].append(answer)
    return grouped


def _summarize_choices(summary: QuestionSummary, answers: list[Answer]) -> None:
    question = summary.question
    counts = Counter(a.choice_id for a in answers)
    summary.answered = len({a.response_id for a in answers})
    summary.labels = [c.label for c in question.choices]
    summary.counts = [counts.get(c.id, 0) for c in question.choices]


def _summarize_scale(summary: QuestionSummary, answers: list[Answer], low: int, high: int) -> None:
    values = [a.number_value for a in answers if a.number_value is not None]
    counts = Counter(values)
    summary.answered = len(values)
    summary.labels = [str(n) for n in range(low, high + 1)]
    summary.counts = [counts.get(n, 0) for n in range(low, high + 1)]
    if values:
        summary.average = round(sum(values) / len(values), 1)


def _summarize_text(summary: QuestionSummary, answers: list[Answer]) -> None:
    texts = [a.text_value for a in answers if a.text_value]
    summary.answered = len(texts)
    summary.texts = texts[:TEXT_SAMPLE_SIZE]


def _summarize_dates(summary: QuestionSummary, answers: list[Answer]) -> None:
    days = sorted(a.date_value for a in answers if a.date_value is not None)
    summary.answered = len(days)
    if not days:
        return
    summary.earliest, summary.latest = days[0], days[-1]
    months = Counter(day.strftime("%Y-%m") for day in days)
    summary.labels = sorted(months)
    summary.counts = [months[m] for m in summary.labels]


def summarize(survey) -> list[QuestionSummary]:
    grouped = _answers_by_question(survey)
    summaries = []
    for question in survey.questions:
        summary = QuestionSummary(question=question)
        answers = grouped.get(question.id, [])
        if question.type in (SINGLE_CHOICE, MULTIPLE_CHOICE):
            _summarize_choices(summary, answers)
        elif question.type == RATING:
            _summarize_scale(summary, answers, 1, (question.settings or {}).get("scale", 5))
        elif question.type == NPS:
            _summarize_scale(summary, answers, 0, 10)
        elif question.type in (SHORT_TEXT, LONG_TEXT):
            _summarize_text(summary, answers)
        elif question.type == DATE:
            _summarize_dates(summary, answers)
        summaries.append(summary)
    return summaries
