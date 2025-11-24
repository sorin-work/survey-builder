import pytest

from survey_builder.domain.settings import parse_settings


def test_short_text_defaults_to_type_limit():
    settings, errors = parse_settings("short_text", {})
    assert errors == {}
    assert settings == {"max_length": 1000}


def test_text_min_and_max_length():
    settings, errors = parse_settings("long_text", {"min_length": "20", "max_length": "400"})
    assert errors == {}
    assert settings == {"min_length": 20, "max_length": 400}


@pytest.mark.parametrize(
    "form, field",
    [
        ({"max_length": "abc"}, "max_length"),
        ({"max_length": "0"}, "max_length"),
        ({"max_length": "5000"}, "max_length"),
        ({"min_length": "-1"}, "min_length"),
        ({"min_length": "50", "max_length": "10"}, "min_length"),
    ],
)
def test_text_length_errors(form, field):
    _, errors = parse_settings("short_text", form)
    assert field in errors


def test_multiple_choice_limits():
    settings, errors = parse_settings("multiple_choice", {"min_choices": "1", "max_choices": "3"})
    assert errors == {}
    assert settings == {"min_choices": 1, "max_choices": 3}

    _, errors = parse_settings("multiple_choice", {"min_choices": "4", "max_choices": "2"})
    assert "min_choices" in errors

    _, errors = parse_settings("multiple_choice", {"max_choices": "0"})
    assert "max_choices" in errors


def test_rating_scale_and_labels():
    settings, errors = parse_settings(
        "rating", {"scale": "10", "low_label": " Poor ", "high_label": "Great"}
    )
    assert errors == {}
    assert settings == {"scale": 10, "low_label": "Poor", "high_label": "Great"}


@pytest.mark.parametrize("scale", ["2", "11", "x"])
def test_rating_scale_out_of_range(scale):
    _, errors = parse_settings("rating", {"scale": scale})
    assert "scale" in errors


def test_rating_label_too_long():
    _, errors = parse_settings("rating", {"low_label": "x" * 61})
    assert "low_label" in errors


def test_nps_labels():
    settings, errors = parse_settings("nps", {"low_label": "Never", "high_label": "Surely"})
    assert errors == {}
    assert settings == {"low_label": "Never", "high_label": "Surely"}


def test_date_bounds():
    settings, errors = parse_settings("date", {"min_date": "2026-01-01", "max_date": "2026-12-31"})
    assert errors == {}
    assert settings == {"min_date": "2026-01-01", "max_date": "2026-12-31"}

    _, errors = parse_settings("date", {"min_date": "2026-12-31", "max_date": "2026-01-01"})
    assert "min_date" in errors

    _, errors = parse_settings("date", {"min_date": "31/12/2026"})
    assert "min_date" in errors


def test_single_choice_has_no_settings():
    assert parse_settings("single_choice", {"scale": "4"}) == ({}, {})
