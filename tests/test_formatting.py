import pytest

from survey_builder.formatting import duration


@pytest.mark.parametrize(
    "seconds, text",
    [(None, ""), (0, "0s"), (45, "45s"), (60, "1m 00s"), (200, "3m 20s"), (3900, "1h 05m")],
)
def test_duration(seconds, text):
    assert duration(seconds) == text
