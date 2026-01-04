from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Tuple
from zoneinfo import ZoneInfo


def next_sunday_midnight(now: datetime) -> datetime:
    """Next Sunday 00:00 in same timezone. If today is Sunday, returns today's midnight."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    # weekday(): Mon=0 .. Sun=6
    days_ahead = (6 - now.weekday()) % 7
    start_date = (now + timedelta(days=days_ahead)).date()
    return datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=now.tzinfo)


def week_window_starting_sunday(now: datetime) -> Tuple[datetime, datetime]:
    start = next_sunday_midnight(now)
    end = start + timedelta(days=7)
    return start, end


def week_window_from_date(start_d: date, tz: ZoneInfo) -> Tuple[datetime, datetime]:
    """
    Return [start, start+7days) where start is local midnight at start_d.
    This includes the full 24-hour period starting on start_d and the following 6 days.
    """
    start = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=tz)
    end = start + timedelta(days=7)
    return start, end

