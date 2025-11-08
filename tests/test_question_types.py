import pytest

from survey_builder.domain.question_types import (
    CHOICE_TYPES,
    QUESTION_TYPES,
    default_settings,
    get_type,
)


def test_all_supported_types_are_registered():
    assert set(QUESTION_TYPES) == {
        "short_text",
        "long_text",
        "single_choice",
        "multiple_choice",
        "rating",
        "nps",
        "date",
    }


def test_choice_types():
    assert {"single_choice", "multiple_choice"} == CHOICE_TYPES


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        get_type("slider")


def test_default_settings_are_copies():
    settings = default_settings("rating")
    settings["scale"] = 10
    assert default_settings("rating") == {"scale": 5}
