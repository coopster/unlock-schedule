from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from unlock_schedule.core.models import Interval
from unlock_schedule.core.schedule.intervals import merge_intervals, split_interval_by_day


class TestIntervals(unittest.TestCase):
    def test_merge_intervals_touching(self) -> None:
        tz = ZoneInfo("America/New_York")
        a = Interval(
            start=datetime(2025, 1, 1, 10, 0, tzinfo=tz),
            end=datetime(2025, 1, 1, 11, 0, tzinfo=tz),
            sources=("a",),
        )
        b = Interval(
            start=datetime(2025, 1, 1, 11, 0, tzinfo=tz),
            end=datetime(2025, 1, 1, 12, 0, tzinfo=tz),
            sources=("b",),
        )
        merged = merge_intervals([a, b], merge_touching=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].start, a.start)
        self.assertEqual(merged[0].end, b.end)

        not_merged = merge_intervals([a, b], merge_touching=False)
        self.assertEqual(len(not_merged), 2)

    def test_split_interval_by_day(self) -> None:
        tz = ZoneInfo("America/New_York")
        start = datetime(2025, 1, 1, 23, 30, tzinfo=tz)
        end = start + timedelta(hours=2)  # crosses midnight
        iv = Interval(start=start, end=end, sources=("x",))
        segs = split_interval_by_day(iv)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0].start, start)
        self.assertEqual((segs[0].end.hour, segs[0].end.minute), (0, 0))
        self.assertEqual((segs[1].start.hour, segs[1].start.minute), (0, 0))
        self.assertEqual(segs[1].end, end)


if __name__ == "__main__":
    unittest.main()
