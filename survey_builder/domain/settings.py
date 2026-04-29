"""Parsing and validating the per-type settings of a question.

Settings come from the editor form as strings. ``parse_settings`` turns them
into a clean dict for ``Question.settings`` plus a dict of error messages.
"""

from datetime import date

from .question_types import (
    DATE,
    LONG_TEXT,
    MULTIPLE_CHOICE,
    NPS,
    RATING,
    SHORT_TEXT,
    SINGLE_CHOICE,
)

TEXT_LIMITS = {SHORT_TEXT: 1000, LONG_TEXT: 10000}
TEXT_FORMATS = {"": "Any text", "email": "Email address", "number": "Number"}
RATING_SCALES = range(3, 11)
LABEL_MAX = 60


def _int_or_none(raw: str | None, field: str, errors: dict) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        errors[field] = "Enter a whole number."
        return None
    if value < 0:
        errors[field] = "Enter a positive number."
        return None
    return value


def _date_or_none(raw: str | None, field: str, errors: dict) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors[field] = "Enter a date as YYYY-MM-DD."
        return None


def _label(raw: str | None, field: str, errors: dict) -> str:
    value = (raw or "").strip()
    if len(value) > LABEL_MAX:
        errors[field] = f"Keep labels under {LABEL_MAX} characters."
    return value


def parse_settings(qtype: str, form) -> tuple[dict, dict[str, str]]:
    errors: dict[str, str] = {}
    settings: dict = {}

    if qtype in TEXT_LIMITS:
        limit = TEXT_LIMITS[qtype]
        min_length = _int_or_none(form.get("min_length"), "min_length", errors)
        max_length = _int_or_none(form.get("max_length"), "max_length", errors)
        if max_length is not None and not 1 <= max_length <= limit:
            errors["max_length"] = f"Maximum length must be between 1 and {limit}."
        if min_length is not None and max_length is not None and min_length > max_length:
            errors["min_length"] = "Minimum length cannot be more than the maximum."
        settings["max_length"] = max_length or limit
        if min_length:
            settings["min_length"] = min_length
        if qtype == SHORT_TEXT:
            text_format = (form.get("format") or "").strip()
            if text_format not in TEXT_FORMATS:
                errors["format"] = "Pick one of the formats."
            elif text_format:
                settings["format"] = text_format

    elif qtype == SINGLE_CHOICE:
        if form.get("shuffle") in ("on", "1", True):
            settings["shuffle"] = True

    elif qtype == MULTIPLE_CHOICE:
        if form.get("shuffle") in ("on", "1", True):
            settings["shuffle"] = True
        min_choices = _int_or_none(form.get("min_choices"), "min_choices", errors)
        max_choices = _int_or_none(form.get("max_choices"), "max_choices", errors)
        if min_choices is not None and max_choices is not None and min_choices > max_choices:
            errors["min_choices"] = "Minimum cannot be more than the maximum."
        if max_choices == 0:
            errors["max_choices"] = "Allow at least one choice."
        if min_choices:
            settings["min_choices"] = min_choices
        if max_choices:
            settings["max_choices"] = max_choices

    elif qtype == RATING:
        scale = _int_or_none(form.get("scale"), "scale", errors) or 5
        if scale not in RATING_SCALES:
            errors["scale"] = "Scale must be between 3 and 10."
        settings["scale"] = scale
        settings["low_label"] = _label(form.get("low_label"), "low_label", errors)
        settings["high_label"] = _label(form.get("high_label"), "high_label", errors)

    elif qtype == NPS:
        settings["low_label"] = _label(form.get("low_label"), "low_label", errors)
        settings["high_label"] = _label(form.get("high_label"), "high_label", errors)

    elif qtype == DATE:
        min_date = _date_or_none(form.get("min_date"), "min_date", errors)
        max_date = _date_or_none(form.get("max_date"), "max_date", errors)
        if min_date and max_date and min_date > max_date:
            errors["min_date"] = "The earliest date must be before the latest date."
        if min_date:
            settings["min_date"] = min_date.isoformat()
        if max_date:
            settings["max_date"] = max_date.isoformat()

    return settings, errors
