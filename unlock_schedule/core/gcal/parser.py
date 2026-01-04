from __future__ import annotations

from datetime import datetime, tzinfo
from typing import Optional

from unlock_schedule.core.models import Interval


def parse_event_to_interval(
    e: dict,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
    *,
    tz: tzinfo,
) -> Optional[Interval]:
    summary = e.get("summary", "(no title)")

    start_obj = e.get("start", {})
    end_obj = e.get("end", {})

    # Timed event
    if "dateTime" in start_obj and "dateTime" in end_obj:
        start = datetime.fromisoformat(start_obj["dateTime"]).astimezone(tz)
        end = datetime.fromisoformat(end_obj["dateTime"]).astimezone(tz)

    # All-day event
    elif "date" in start_obj and "date" in end_obj:
        return None

    else:
        return None

    if end <= start:
        return None

    # Clamp to window
    if window_start:
        start = max(start, window_start)
    if window_end:
        end = min(end, window_end)

    if end <= start:
        return None

    return Interval(start=start, end=end, sources=(summary,))
