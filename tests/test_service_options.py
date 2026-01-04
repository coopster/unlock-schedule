from __future__ import annotations

import unittest

from unlock_schedule.config import (
    DAY_NAMES,
    DEFAULT_OPTIMIZE,
    DEFAULT_PAD_AFTER_MIN,
    DEFAULT_PAD_BEFORE_MIN,
    MERGE_TOUCHING,
    MAX_INTERVALS,
)
from unlock_schedule.core.service import GenerateOptions


class TestServiceOptions(unittest.TestCase):
    def test_generate_options_from_config(self) -> None:
        opts = GenerateOptions()
        self.assertEqual(opts.pad_before_min, DEFAULT_PAD_BEFORE_MIN)
        self.assertEqual(opts.pad_after_min, DEFAULT_PAD_AFTER_MIN)
        self.assertEqual(opts.optimize, DEFAULT_OPTIMIZE)
        self.assertEqual(opts.day_names, DAY_NAMES)
        self.assertEqual(opts.max_intervals, MAX_INTERVALS)
        self.assertTrue(MERGE_TOUCHING)


if __name__ == "__main__":
    unittest.main()
