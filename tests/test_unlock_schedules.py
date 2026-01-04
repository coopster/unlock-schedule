from __future__ import annotations

import json
from typing import Iterable
import unittest
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo
from unlock_schedule.config import DAY_NAMES, TZ
from unlock_schedule.core.service import override_options, prepare_intervals, build_unlock_rows, GenerateOptions


# An arbitrary stable week start date for testing purposes
WEEK_STARTING = datetime(2026, 1, 4, tzinfo=TZ)

def _parse_hhmm(s: str) -> tuple[int, int]:
    s = s.strip()
    if ":" not in s:
        return int(s), 0
    hh, mm = s.split(":", 1)
    return int(hh), int(mm) if mm else 0


def _expand_dows(dow_range: str) -> Iterable[str]:
    dow_range = dow_range.strip()
    if "-" not in dow_range:
        return [dow_range]
    start_name, end_name = [p.strip() for p in dow_range.split("-", 1)]
    start_idx = DAY_NAMES.index(start_name)
    end_idx = DAY_NAMES.index(end_name)
    if end_idx >= start_idx:
        return DAY_NAMES[start_idx : end_idx + 1]
    # Wrap-around (e.g., Fri-Mon)
    return DAY_NAMES[start_idx:] + DAY_NAMES[: end_idx + 1]


def _evts(dow_range: str, title: str, time_range: str) -> list[dict]:

    """
    Generate a list of events that correspond to a single entry in a test case.

    Args:
        dow_range (str): The days of the week for which this event applies, separated by dashes (e.g. "Mon-Fri").
        title (str): The title of the event.
        time_range (str): The time range for which this event applies, in the format "HH:MM-HH:MM".

    Returns:
        list[dict]: A list of events in the format similar to what is returned by the Google Calendar API.
    """
    events: list[dict] = []
    start_s, end_s = [p.strip() for p in time_range.split("-", 1)]
    sh, sm = _parse_hhmm(start_s)
    eh, em = _parse_hhmm(end_s)

    for dow in _expand_dows(dow_range):
        day_idx = DAY_NAMES.index(dow)
        day_date = (WEEK_STARTING + timedelta(days=day_idx)).date()
        start_dt = datetime.combine(day_date, time(sh, sm), tzinfo=TZ)
        end_dt = datetime.combine(day_date, time(eh, em), tzinfo=TZ)
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
        events.append({
            "summary": title,
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        })
    return events


class TestUnlockSchedules(unittest.TestCase):
    
    def test_busy_week_5_intervals(self) -> None:
        self.run_test("""
Sun|Sunday Morning Service|07:15-12:00                 
Mon-Fri|Head Start|08:00-12:45
Mon-Fri|Head Start Pickup|11:30-12:45
Mon-Fri|Parent Pick-up|13:30-14:45
Tue|Coffee Break|08:00-11:30
Mon|Celebrate Recovery|16:45-20:05
Tue|Council|18:50-19:20
Tue|Congregational Mtg|19:00-21:0  
""", 5)
        
    def test_optimize_opportunity(self) -> None:
        # Unoptimized, 3 intervals
        self.run_test("""
Mon|Block1|08:00-12:00
Tue|Block2|10:00-14:00
Wed|Block3|08:00-14:00
""", 3)
        
        # Optimized, 2 intervals
        self.run_test("""
    Mon|Block1|08:00-12:00
    Tue|Block2|10:00-14:00
    Wed|Block3|08:00-14:00
    """, 2, True)
        
    
    def run_test(self, case: str, row_count: int, optimize: bool = False) -> None:
        # Create the events represented by the case.
        events = [
            evt
            for line in case.splitlines()
            if line.strip()
            for evt in _evts(*line.split("|", 2))
        ]
        
        opts = GenerateOptions()
        if optimize:
            opts = override_options(opts, optimize=True)
        intervals = prepare_intervals(events, options=opts)
        rows = build_unlock_rows(intervals, options=opts)

        # Sanity: expected row count for used intervals.
        used = [r for r in rows if not (r["Start"] == "0000" and r["End"] == "0000")]
        self.assertEqual(len(used), row_count)


if __name__ == "__main__":
    unittest.main()
