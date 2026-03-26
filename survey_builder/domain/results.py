"""Aggregating completed responses into per-question summaries."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from fractions import Fraction

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
    nps: "NpsScore | None" = None

    @property
    def percentages(self) -> list[float]:
        if not self.answered:
            return [0.0 for _ in self.counts]
        return [round(100 * count / self.answered, 1) for count in self.counts]


@dataclass(frozen=True)
class NpsScore:
    promoters: int
    passives: int
    detractors: int

    @property
    def total(self) -> int:
        return self.promoters + self.passives + self.detractors

    @property
    def score(self) -> int | None:
        """Net Promoter Score: % promoters minus % detractors, from -100 to 100."""
        if not self.total:
            return None
        # Round half away from zero, like the usual NPS calculators do.
        exact = Fraction(self.promoters - self.detractors, self.total) * 100
        rounded = int(abs(exact) + Fraction(1, 2))
        return rounded if exact >= 0 else -rounded


def nps_score(values) -> NpsScore:
    values = list(values)
    return NpsScore(
        promoters=sum(1 for v in values if v >= 9),
        passives=sum(1 for v in values if 7 <= v <= 8),
        detractors=sum(1 for v in values if v <= 6),
    )


@dataclass(frozen=True)
class Period:
    """An inclusive range of submission dates (UTC). Either end may be open."""

    start: date | None = None
    end: date | None = None

    @classmethod
    def from_args(cls, args) -> "Period":
        def parse(raw):
            try:
                return date.fromisoformat(raw) if raw else None
            except ValueError:
                return None

        return cls(parse(args.get("from")), parse(args.get("to")))

    @property
    def is_open(self) -> bool:
        return self.start is None and self.end is None

    def conditions(self) -> list:
        conditions = []
        if self.start:
            conditions.append(Response.completed_at >= datetime.combine(self.start, time.min))
        if self.end:
            next_day = datetime.combine(self.end + timedelta(days=1), time.min)
            conditions.append(Response.completed_at < next_day)
        return conditions

    def as_args(self) -> dict[str, str]:
        args = {}
        if self.start:
            args["from"] = self.start.isoformat()
        if self.end:
            args["to"] = self.end.isoformat()
        return args


ALL_TIME = Period()


def completed_filter(survey, period: Period = ALL_TIME) -> list:
    return [
        Response.survey_id == survey.id,
        Response.completed_at.is_not(None),
        *period.conditions(),
    ]


def completed_response_count(survey, period: Period = ALL_TIME) -> int:
    return db.session.scalar(
        select(db.func.count(Response.id)).where(*completed_filter(survey, period))
    )


@dataclass(frozen=True)
class Funnel:
    started: int
    completed: int
    median_seconds: int | None

    @property
    def completion_rate(self) -> int | None:
        if not self.started:
            return None
        return round(100 * self.completed / self.started)


def funnel(survey, period: Period = ALL_TIME) -> Funnel:
    """How many people started vs finished, and how long finishing took."""
    started_conditions = [Response.survey_id == survey.id]
    if period.start:
        started_conditions.append(Response.started_at >= datetime.combine(period.start, time.min))
    if period.end:
        next_day = datetime.combine(period.end + timedelta(days=1), time.min)
        started_conditions.append(Response.started_at < next_day)
    started = db.session.scalar(select(db.func.count(Response.id)).where(*started_conditions))
    rows = db.session.execute(
        select(Response.started_at, Response.completed_at).where(*completed_filter(survey, period))
    ).all()
    durations = sorted((done - begun).total_seconds() for begun, done in rows)
    median = None
    if durations:
        middle = len(durations) // 2
        if len(durations) % 2:
            median = durations[middle]
        else:
            median = (durations[middle - 1] + durations[middle]) / 2
    return Funnel(
        started=max(started, len(rows)),
        completed=len(rows),
        median_seconds=None if median is None else int(median),
    )


def daily_counts(survey, period: Period = ALL_TIME) -> list[tuple[date, int]]:
    """Completed responses per day, including days without any, oldest first."""
    stamps = db.session.scalars(
        select(Response.completed_at).where(*completed_filter(survey, period))
    ).all()
    if not stamps:
        return []
    per_day = Counter(stamp.date() for stamp in stamps)
    first = period.start or min(per_day)
    last = period.end or max(per_day)
    days = []
    day = first
    while day <= last:
        days.append((day, per_day.get(day, 0)))
        day += timedelta(days=1)
    return days


def _answers_by_question(survey, period: Period) -> dict[int, list[Answer]]:
    rows = db.session.scalars(
        select(Answer)
        .join(Response)
        .where(*completed_filter(survey, period))
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


def summarize(survey, period: Period = ALL_TIME) -> list[QuestionSummary]:
    grouped = _answers_by_question(survey, period)
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
            summary.nps = nps_score(a.number_value for a in answers if a.number_value is not None)
        elif question.type in (SHORT_TEXT, LONG_TEXT):
            _summarize_text(summary, answers)
        elif question.type == DATE:
            _summarize_dates(summary, answers)
        summaries.append(summary)
    return summaries
