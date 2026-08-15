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


def timeago(moment, now=None) -> str:
    """'just now', '5 minutes ago', '3 hours ago', '2 days ago' or a date."""
    from datetime import UTC, datetime

    if moment is None:
        return ""
    now = now or datetime.now(UTC).replace(tzinfo=None)
    seconds = int((now - moment).total_seconds())
    if seconds < 60:
        return "just now"
    for unit, size in (("minute", 60), ("hour", 3600), ("day", 86400)):
        limit = {"minute": 3600, "hour": 86400, "day": 86400 * 30}[unit]
        if seconds < limit:
            value = seconds // size
            return f"{value} {unit}{'s' if value != 1 else ''} ago"
    return f"on {moment.strftime('%Y-%m-%d')}"
