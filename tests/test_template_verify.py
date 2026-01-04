from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from unlock_schedule.config import DAY_NAMES, MAX_INTERVALS
from unlock_schedule.core.models import Interval
from unlock_schedule.core.schedule.template import build_weekly_template
from unlock_schedule.core.schedule.verify import build_required_grid, verify_rows_match_required


class TestTemplateVerify(unittest.TestCase):
    def test_template_rows_round_trip_verify(self) -> None:
        tz = ZoneInfo("America/New_York")
        intervals = [
            Interval(
                start=datetime(2025, 1, 6, 9, 0, tzinfo=tz),  # Mon
                end=datetime(2025, 1, 6, 10, 0, tzinfo=tz),
                sources=("Mon",),
            ),
            Interval(
                start=datetime(2025, 1, 7, 9, 0, tzinfo=tz),  # Tue
                end=datetime(2025, 1, 7, 10, 0, tzinfo=tz),
                sources=("Tue",),
            ),
        ]
        rows = build_weekly_template(intervals, day_names=DAY_NAMES, max_intervals=MAX_INTERVALS)
        required = build_required_grid(intervals)
        verify_rows_match_required(rows, required)


if __name__ == "__main__":
    unittest.main()
