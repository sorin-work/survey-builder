"""Turning submitted form values into validated answers.

Each question is rendered as a form field named ``q<question id>``. Choice
questions submit choice ids; multiple choice questions may submit the field
several times.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from .question_types import DATE, LONG_TEXT, MULTIPLE_CHOICE, NPS, RATING, SHORT_TEXT, SINGLE_CHOICE

REQUIRED_MESSAGE = "This question is required."
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NUMBER_RE = re.compile(r"^-?\d+([.,]\d+)?$")


def field_name(question) -> str:
    return f"q{question.id}"


@dataclass
class ParsedAnswer:
    question_id: int
    text: str | None = None
    number: int | None = None
    day: date | None = None
    choice_ids: list[int] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.text and self.number is None and self.day is None and not self.choice_ids


def _getlist(form, name: str) -> list[str]:
    if hasattr(form, "getlist"):
        return form.getlist(name)
    value = form.get(name)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _parse_text(question, raw: str, answer: ParsedAnswer) -> str | None:
    settings = question.settings or {}
    value = raw.strip()
    if not value:
        return REQUIRED_MESSAGE if question.required else None
    min_length = settings.get("min_length")
    max_length = settings.get("max_length")
    if min_length and len(value) < min_length:
        return f"Please write at least {min_length} characters."
    if max_length and len(value) > max_length:
        return f"Please keep it under {max_length} characters."
    text_format = settings.get("format")
    if text_format == "email" and not EMAIL_RE.match(value):
        return "Please enter a valid email address."
    if text_format == "number" and not NUMBER_RE.match(value):
        return "Please enter a number."
    answer.text = value
    return None


def _parse_choices(question, raws: list[str], answer: ParsedAnswer) -> str | None:
    valid_ids = {choice.id for choice in question.choices}
    chosen: list[int] = []
    for raw in raws:
        try:
            choice_id = int(raw)
        except ValueError:
            return "Please choose one of the options."
        if choice_id not in valid_ids:
            return "Please choose one of the options."
        if choice_id not in chosen:
            chosen.append(choice_id)

    if not chosen:
        return REQUIRED_MESSAGE if question.required else None
    if question.type == SINGLE_CHOICE and len(chosen) > 1:
        return "Please choose only one option."
    if question.type == MULTIPLE_CHOICE:
        settings = question.settings or {}
        min_choices = settings.get("min_choices")
        max_choices = settings.get("max_choices")
        if min_choices and len(chosen) < min_choices:
            return f"Please choose at least {min_choices} options."
        if max_choices and len(chosen) > max_choices:
            return f"Please choose at most {max_choices} options."
    answer.choice_ids = chosen
    return None


def _parse_scale(question, raw: str, answer: ParsedAnswer) -> str | None:
    raw = raw.strip()
    if not raw:
        return REQUIRED_MESSAGE if question.required else None
    low, high = (0, 10) if question.type == NPS else (1, (question.settings or {}).get("scale", 5))
    try:
        value = int(raw)
    except ValueError:
        return f"Please pick a number from {low} to {high}."
    if not low <= value <= high:
        return f"Please pick a number from {low} to {high}."
    answer.number = value
    return None


def _parse_date(question, raw: str, answer: ParsedAnswer) -> str | None:
    raw = raw.strip()
    if not raw:
        return REQUIRED_MESSAGE if question.required else None
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        return "Please enter a valid date."
    settings = question.settings or {}
    if settings.get("min_date") and value < date.fromisoformat(settings["min_date"]):
        return f"Please enter a date on or after {settings['min_date']}."
    if settings.get("max_date") and value > date.fromisoformat(settings["max_date"]):
        return f"Please enter a date on or before {settings['max_date']}."
    answer.day = value
    return None


def parse_answer(question, form) -> tuple[ParsedAnswer, str | None]:
    """Parse the answer to one question. Returns the answer and an error message."""
    answer = ParsedAnswer(question_id=question.id)
    name = field_name(question)
    if question.type in (SHORT_TEXT, LONG_TEXT):
        error = _parse_text(question, form.get(name) or "", answer)
    elif question.type in (SINGLE_CHOICE, MULTIPLE_CHOICE):
        error = _parse_choices(question, _getlist(form, name), answer)
    elif question.type in (RATING, NPS):
        error = _parse_scale(question, form.get(name) or "", answer)
    elif question.type == DATE:
        error = _parse_date(question, form.get(name) or "", answer)
    else:
        raise ValueError(f"unknown question type: {question.type!r}")
    return answer, error


def parse_page(questions, form) -> tuple[list[ParsedAnswer], dict[int, str]]:
    """Parse every question on a page. Errors are keyed by question id."""
    answers, errors = [], {}
    for question in questions:
        answer, error = parse_answer(question, form)
        if error:
            errors[question.id] = error
        else:
            answers.append(answer)
    return answers, errors
