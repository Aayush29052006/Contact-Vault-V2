from datetime import datetime, timezone
import re


def derive_name_from_email(email):
    """Best-effort name guess from an email's local part, e.g.
    'jane.doe@example.com' -> 'Jane Doe'. Used when someone submits
    just an email with no name."""
    local_part = email.split("@")[0]
    words = [w for w in re.split(r"[._\-+]+", local_part) if w]
    if not words:
        return email
    return " ".join(word.capitalize() for word in words)


def time_ago(dt):
    """Turn a UTC datetime into a short human-friendly relative string,
    e.g. '2 minutes ago', 'Yesterday', '3 days ago'. SQLite loses
    timezone info on round-trip, so a naive datetime is assumed to be
    UTC (that's what ActivityLog always stores)."""
    if dt is None:
        return ""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 0:
        seconds = 0

    if seconds < 60:
        return "Just now"

    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = int(hours // 24)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"

    weeks = int(days // 7)
    if weeks < 5:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    months = int(days // 30)
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = int(days // 365)
    return f"{years} year{'s' if years != 1 else ''} ago"
