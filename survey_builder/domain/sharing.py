"""Publishing a survey and deciding whether its public link accepts answers."""

import secrets
from datetime import datetime

from ..models import utcnow
from .results import completed_response_count

DRAFT = "draft"
PUBLISHED = "published"
CLOSED = "closed"


def new_share_token() -> str:
    return secrets.token_urlsafe(12)


def publish_problems(survey) -> list[str]:
    """Reasons the survey cannot be published yet (empty list when it can)."""
    problems = []
    if not survey.questions:
        problems.append("Add at least one question before publishing.")
    for question in survey.questions:
        if question.type in ("single_choice", "multiple_choice") and not question.choices:
            problems.append(f"“{question.prompt}” has no options.")
    return problems


# Why a published link does not accept answers.
REASON_CLOSED = "closed"
REASON_DRAFT = "draft"
REASON_DATE = "date"
REASON_LIMIT = "limit"


def closed_reason(survey, now: datetime | None = None) -> str | None:
    """None when the survey accepts responses, otherwise one of the REASON_* values."""
    if survey.status == CLOSED:
        return REASON_CLOSED
    if survey.status != PUBLISHED:
        return REASON_DRAFT
    now = now or utcnow()
    # "Close on 10 March" means respondents can still answer during 10 March.
    if survey.closes_on and now.date() > survey.closes_on:
        return REASON_DATE
    limit = survey.response_limit
    if limit is not None and completed_response_count(survey) > limit:
        return REASON_LIMIT
    return None


def is_accepting_responses(survey, now: datetime | None = None) -> bool:
    return closed_reason(survey, now) is None
