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


def test_timeago():
    from datetime import datetime, timedelta

    from survey_builder.formatting import timeago

    now = datetime(2026, 8, 15, 12, 0)
    assert timeago(now - timedelta(seconds=30), now) == "just now"
    assert timeago(now - timedelta(minutes=1), now) == "1 minute ago"
    assert timeago(now - timedelta(minutes=59), now) == "59 minutes ago"
    assert timeago(now - timedelta(hours=5), now) == "5 hours ago"
    assert timeago(now - timedelta(days=2), now) == "2 days ago"
    assert timeago(datetime(2026, 1, 3), now) == "on 2026-01-03"
    assert timeago(None) == ""
