"""India Standard Time (IST) helpers.

DB stores naive UTC datetimes (legacy `datetime.utcnow()`). Display and
\"today\" boundaries for limits use Asia/Kolkata.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def utc_naive_to_ist(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(IST)
    return dt.replace(tzinfo=UTC).astimezone(IST)


def format_time_ampm_ist(dt: datetime | None) -> str:
    """e.g. 9:05 PM — for chat history sidebar (IST)."""
    local = utc_naive_to_ist(dt)
    if local is None:
        return ""
    hour12 = local.hour % 12 or 12
    return f"{hour12}:{local.strftime('%M %p')}"


def format_timestamp_gemini_ist(dt: datetime | None) -> str:
    """Bracket timestamps in Gemini context (IST wall clock)."""
    local = utc_naive_to_ist(dt)
    if local is None:
        return ""
    return local.strftime("%Y-%m-%d %H:%M")


# Matches prefixes we attach in Gemini history: "[2026-05-02 16:40] hello"
_LEAKED_GEMINI_TS = re.compile(
    r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]\s*",
)


def strip_leaked_gemini_timestamps(text: str) -> str:
    """Remove echoed `[YYYY-MM-DD HH:MM]` prefixes from model output (prompt says never quote them)."""
    if not text:
        return text
    return _LEAKED_GEMINI_TS.sub("", text).strip()


def split_model_bubbles(text: str) -> list[str]:
    """Split model output on app delimiters, treating leaked timestamps as bubble boundaries."""
    if not text:
        return []
    normalized = _LEAKED_GEMINI_TS.sub("|", text.strip())
    return [
        strip_leaked_gemini_timestamps(part)
        for part in normalized.split("|")
        if strip_leaked_gemini_timestamps(part)
    ]


def ist_day_start_utc_naive(d: date) -> datetime:
    """Start of IST calendar day `d`, as naive UTC (for SQL compares)."""
    local = datetime.combine(d, time.min, tzinfo=IST)
    return local.astimezone(UTC).replace(tzinfo=None)


def ist_day_end_utc_naive(d: date) -> datetime:
    return ist_day_start_utc_naive(d + timedelta(days=1))


def ist_today_date() -> date:
    return datetime.now(IST).date()
