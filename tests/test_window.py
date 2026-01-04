from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from unlock_schedule.core.window import next_sunday_midnight, week_window_from_date


class TestWindow(unittest.TestCase):
    def test_week_window_from_date_is_seven_days(self) -> None:
        tz = ZoneInfo("America/New_York")
        start, end = week_window_from_date(date(2025, 1, 1), tz)
        self.assertEqual(start.tzinfo, tz)
        self.assertTrue(start.isoformat().endswith("00:00:00-05:00"))
        self.assertEqual((end - start).days, 7)

    def test_next_sunday_midnight(self) -> None:
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 6, 13, 0, tzinfo=tz)  # Mon
        sunday = next_sunday_midnight(now)
        self.assertEqual(sunday.weekday(), 6)  # Sunday
        self.assertEqual((sunday.hour, sunday.minute), (0, 0))


if __name__ == "__main__":
    unittest.main()
