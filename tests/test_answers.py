from dataclasses import dataclass, field
from datetime import date

import pytest
from werkzeug.datastructures import MultiDict

from survey_builder.domain.answers import REQUIRED_MESSAGE, parse_answer, parse_page


@dataclass
class C:
    id: int
    label: str = ""


@dataclass
class Q:
    id: int
    type: str
    required: bool = False
    settings: dict = field(default_factory=dict)
    choices: list = field(default_factory=list)


def form(**values):
    return MultiDict(values)


def test_short_text_is_trimmed():
    answer, error = parse_answer(Q(1, "short_text"), form(q1="  Ana  "))
    assert error is None
    assert answer.text == "Ana"


def test_optional_text_may_be_empty():
    answer, error = parse_answer(Q(1, "long_text"), form())
    assert error is None
    assert answer.is_empty


def test_required_text_missing():
    _, error = parse_answer(Q(1, "short_text", required=True), form(q1=""))
    assert error == REQUIRED_MESSAGE


def test_text_length_rules():
    question = Q(1, "long_text", settings={"min_length": 5, "max_length": 10})
    assert parse_answer(question, form(q1="abc"))[1] == "Please write at least 5 characters."
    assert parse_answer(question, form(q1="a" * 11))[1] == "Please keep it under 10 characters."
    assert parse_answer(question, form(q1="just ok"))[1] is None


def test_single_choice():
    question = Q(1, "single_choice", choices=[C(10), C(11)])
    answer, error = parse_answer(question, form(q1="11"))
    assert error is None
    assert answer.choice_ids == [11]


@pytest.mark.parametrize("raw", ["99", "abc"])
def test_single_choice_rejects_unknown_options(raw):
    question = Q(1, "single_choice", choices=[C(10), C(11)])
    assert parse_answer(question, form(q1=raw))[1] == "Please choose one of the options."


def test_single_choice_rejects_two_options():
    question = Q(1, "single_choice", choices=[C(10), C(11)])
    values = MultiDict([("q1", "10"), ("q1", "11")])
    assert parse_answer(question, values)[1] == "Please choose only one option."


def test_multiple_choice_limits_and_duplicates():
    question = Q(
        1,
        "multiple_choice",
        settings={"min_choices": 2, "max_choices": 3},
        choices=[C(1), C(2), C(3), C(4)],
    )
    values = MultiDict([("q1", "1")])
    assert parse_answer(question, values)[1] == "Please choose at least 2 options."
    values = MultiDict([("q1", v) for v in "1234"])
    assert parse_answer(question, values)[1] == "Please choose at most 3 options."
    values = MultiDict([("q1", v) for v in "1223"])
    answer, error = parse_answer(question, values)
    assert error is None
    assert answer.choice_ids == [1, 2, 3]


def test_required_multiple_choice():
    question = Q(1, "multiple_choice", required=True, choices=[C(1)])
    assert parse_answer(question, form())[1] == REQUIRED_MESSAGE


def test_rating_bounds():
    question = Q(1, "rating", settings={"scale": 4})
    assert parse_answer(question, form(q1="4"))[0].number == 4
    assert parse_answer(question, form(q1="5"))[1] == "Please pick a number from 1 to 4."
    assert parse_answer(question, form(q1="0"))[1] == "Please pick a number from 1 to 4."


def test_nps_accepts_zero_to_ten():
    question = Q(1, "nps")
    assert parse_answer(question, form(q1="0"))[0].number == 0
    assert parse_answer(question, form(q1="10"))[0].number == 10
    assert parse_answer(question, form(q1="11"))[1] is not None
    assert parse_answer(question, form(q1="seven"))[1] is not None


def test_date_answers_and_bounds():
    question = Q(1, "date", settings={"min_date": "2026-01-01", "max_date": "2026-01-31"})
    assert parse_answer(question, form(q1="2026-01-15"))[0].day == date(2026, 1, 15)
    assert "on or after" in parse_answer(question, form(q1="2025-12-31"))[1]
    assert "on or before" in parse_answer(question, form(q1="2026-02-01"))[1]
    assert parse_answer(question, form(q1="15/01/2026"))[1] == "Please enter a valid date."


def test_parse_page_collects_errors_by_question():
    questions = [Q(1, "short_text", required=True), Q(2, "nps"), Q(3, "rating")]
    answers, errors = parse_page(questions, form(q2="9", q3="x"))
    assert [a.question_id for a in answers] == [2]
    assert set(errors) == {1, 3}
