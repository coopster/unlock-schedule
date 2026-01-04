from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import List

from unlock_schedule.core.models import Interval


def merge_intervals(intervals: List[Interval], merge_touching: bool = True) -> List[Interval]:
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: (x.start, x.end))
    merged: List[Interval] = []
    cur = intervals[0]

    for nxt in intervals[1:]:
        overlaps = nxt.start <= cur.end if merge_touching else nxt.start < cur.end
        if overlaps:
            new_end = max(cur.end, nxt.end)
            new_sources = tuple(dict.fromkeys(cur.sources + nxt.sources))  # unique, keep order
            cur = Interval(start=cur.start, end=new_end, sources=new_sources)
        else:
            merged.append(cur)
            cur = nxt
    merged.append(cur)
    return merged


def apply_padding(
    interval: Interval,
    before_min: int,
    after_min: int
) -> Interval:
    start = interval.start - timedelta(minutes=before_min)
    end = interval.end + timedelta(minutes=after_min)
    return Interval(start=start, end=end, sources=interval.sources)


def split_interval_by_day(iv: Interval) -> List[Interval]:
    """
    Split an interval at midnight boundaries into per-day segments.
    Returns segments each contained within a single calendar day.
    """
    segments: List[Interval] = []
    cur_start = iv.start
    cur_end = iv.end

    if cur_start.tzinfo is None:
        raise ValueError("Interval.start must be timezone-aware")
    tz = cur_start.tzinfo

    while cur_start.date() < cur_end.date():
        next_midnight = datetime.combine(cur_start.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
        segments.append(Interval(start=cur_start, end=next_midnight, sources=iv.sources))
        cur_start = next_midnight

    segments.append(Interval(start=cur_start, end=cur_end, sources=iv.sources))
    return segments
