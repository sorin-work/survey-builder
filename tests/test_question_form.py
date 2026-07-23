from dataclasses import dataclass, field

from survey_builder.domain.question_form import parse_question_form


@dataclass
class C:
    id: int
    label: str


@dataclass
class Q:
    type: str
    choices: list = field(default_factory=list)
    prompt: str = ""
    help_text: str = ""
    required: bool = False
    settings: dict = field(default_factory=dict)


def test_changes_are_applied():
    question = Q("single_choice", [C(1, "A"), C(2, "B")])
    changes, errors = parse_question_form(
        question, {"prompt": " Pick ", "required": "on", "choice_1": "Alpha"}
    )
    assert errors == {}
    changes.apply(question)
    assert question.prompt == "Pick" and question.required
    assert [c.label for c in question.choices] == ["Alpha", "B"]


def test_errors_are_collected():
    question = Q("rating")
    _, errors = parse_question_form(question, {"prompt": "", "help_text": "x" * 501, "scale": "1"})
    assert set(errors) == {"prompt", "help_text", "scale"}


def test_bulk_choices_skip_blanks_bullets_and_duplicates():
    from survey_builder.domain.question_form import parse_bulk_choices

    labels, error = parse_bulk_choices("Red\n\n- Green\n* blue\n• Yellow\nred\nGreen", ["Blue"])
    assert error is None
    assert labels == ["Red", "Green", "Yellow"]


def test_bulk_choices_errors():
    from survey_builder.domain.question_form import parse_bulk_choices

    assert parse_bulk_choices("\n \n", [])[1] == "Paste at least one new option, one per line."
    assert "at most 50" in parse_bulk_choices("\n".join(f"o{i}" for i in range(51)), [])[1]
    assert "under 300" in parse_bulk_choices("x" * 301, [])[1]
