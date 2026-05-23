import pytest

from survey_builder.formatting import duration


@pytest.mark.parametrize(
    "seconds, text",
    [(None, ""), (0, "0s"), (45, "45s"), (60, "1m 00s"), (200, "3m 20s"), (3900, "1h 05m")],
)
def test_duration(seconds, text):
    assert duration(seconds) == text


def test_nl2br_keeps_line_breaks():
    from survey_builder.formatting import nl2br

    assert str(nl2br("one\ntwo\r\nthree")) == "one<br>two<br>three"
    assert str(nl2br(None)) == ""


def test_nl2br_escapes_html():
    from survey_builder.formatting import nl2br

    html = str(nl2br('<img src=x onerror="alert(1)">\n<b>bold</b> & co'))
    assert (
        html == "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;<br>&lt;b&gt;bold&lt;/b&gt; &amp; co"
    )
