"""Small formatting helpers used as Jinja filters."""

from markupsafe import Markup, escape


def duration(seconds: int | float | None) -> str:
    """Human friendly duration: 45s, 3m 20s, 1h 05m."""
    if seconds is None:
        return ""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def nl2br(text: str | None) -> Markup:
    """Keep the line breaks respondents typed in long answers."""
    if not text:
        return Markup("")
    lines = text.replace("\r\n", "\n").split("\n")
    # Respondent text is untrusted: escape every line, only the <br> is markup.
    return Markup("<br>").join(escape(line) for line in lines)
