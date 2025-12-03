"""Publishing a survey and deciding whether its public link accepts answers."""

import secrets

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


def is_accepting_responses(survey) -> bool:
    return survey.status == PUBLISHED
