"""Small formatting helpers used as Jinja filters."""


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
