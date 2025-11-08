"""The question types a survey can contain and their default settings."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuestionType:
    key: str
    label: str
    has_choices: bool = False
    defaults: dict = field(default_factory=dict)


SHORT_TEXT = "short_text"
LONG_TEXT = "long_text"
SINGLE_CHOICE = "single_choice"
MULTIPLE_CHOICE = "multiple_choice"
RATING = "rating"
NPS = "nps"
DATE = "date"

QUESTION_TYPES: dict[str, QuestionType] = {
    t.key: t
    for t in [
        QuestionType(SHORT_TEXT, "Short text", defaults={"max_length": 200}),
        QuestionType(LONG_TEXT, "Long text", defaults={"max_length": 5000}),
        QuestionType(SINGLE_CHOICE, "Single choice", has_choices=True),
        QuestionType(MULTIPLE_CHOICE, "Multiple choice", has_choices=True),
        QuestionType(RATING, "Rating", defaults={"scale": 5}),
        QuestionType(NPS, "Net Promoter Score"),
        QuestionType(DATE, "Date"),
    ]
}

CHOICE_TYPES = frozenset(k for k, t in QUESTION_TYPES.items() if t.has_choices)


def get_type(key: str) -> QuestionType:
    try:
        return QUESTION_TYPES[key]
    except KeyError:
        raise ValueError(f"unknown question type: {key!r}") from None


def default_settings(key: str) -> dict:
    return dict(get_type(key).defaults)
