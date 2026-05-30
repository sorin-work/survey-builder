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
