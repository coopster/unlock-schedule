from __future__ import annotations

from typing import Dict, List, Tuple
from unlock_schedule.core.models import Interval
from unlock_schedule.core.schedule.intervals import split_interval_by_day


def to_hhmm(dt) -> str:
    return dt.strftime("%H%M")


def hms_day_index(dt) -> int:
    """
    Convert dt to HMS day index: Sun=0..Sat=6.
    Python weekday: Mon=0..Sun=6
    """
    py = dt.weekday()
    return (py + 1) % 7  # Mon->1 ... Sat->6, Sun->0


def build_weekly_template(intervals: List[Interval], *, day_names: Tuple[str, ...], max_intervals: int) -> List[dict]:
    """
    Group intervals by identical (startHHMM, endHHMM), set day flags.
    Returns exactly max_intervals rows (pads unused with 0000,0000 and no days selected).
    """
    grouped: Dict[Tuple[str, str], Dict[str, int]] = {}
    if len(day_names) != 7:
        raise ValueError(f"day_names must have length 7 (got {len(day_names)})")

    for iv in intervals:
        for seg in split_interval_by_day(iv):
            start_h = to_hhmm(seg.start)
            end_h = to_hhmm(seg.end)

            if start_h == end_h:
                continue

            key = (start_h, end_h)
            if key not in grouped:
                grouped[key] = {d: 0 for d in day_names}
                grouped[key]["Holidays"] = 0

            day_idx = hms_day_index(seg.start)
            grouped[key][day_names[day_idx]] = 1

    keys_sorted = sorted(grouped.keys(), key=lambda k: (k[0], k[1]))

    if len(keys_sorted) > max_intervals:
        raise SystemExit(
            f"ERROR: This week requires {len(keys_sorted)} distinct time windows, "
            f"but HMS supports only {max_intervals}.\n"
            f"Distinct windows were: {keys_sorted}\n"
            f"Tip: Standardize event times (e.g., fixed morning and pickup windows) or reduce variability."
        )

    rows: List[dict] = []
    for i, k in enumerate(keys_sorted, start=1):
        start_h, end_h = k
        rows.append(
            {
                "Interval": i,
                "Start": start_h,
                "End": end_h,
                **{d: grouped[k][d] for d in day_names},
                "Holidays": grouped[k]["Holidays"],
            }
        )

    while len(rows) < max_intervals:
        idx = len(rows) + 1
        rows.append(
            {
                "Interval": idx,
                "Start": "0000",
                "End": "0000",
                **{d: 0 for d in day_names},
                "Holidays": 0,
            }
        )

    return rows
