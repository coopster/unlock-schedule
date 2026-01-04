from __future__ import annotations

from typing import List

from unlock_schedule.core.schedule.intervals import split_interval_by_day
from unlock_schedule.core.schedule.template import hms_day_index


def _interval_minutes(iv) -> tuple[int, int]:
    return (iv.start.hour * 60 + iv.start.minute, iv.end.hour * 60 + iv.end.minute)


def build_required_grid(intervals) -> List[List[bool]]:
    """
    Returns grid[day][minute] = True if unlocked at that minute for that day.
    day index: 0=Sun..6=Sat
    minute: 0..1439
    """
    grid = [[False] * 1440 for _ in range(7)]

    for iv in intervals:
        for seg in split_interval_by_day(iv):
            d = hms_day_index(seg.start)
            s, e = _interval_minutes(seg)
            # seg.end could be midnight of next day; represent as 1440
            if seg.end.hour == 0 and seg.end.minute == 0 and seg.end.date() != seg.start.date():
                e = 1440
            # Clamp to 0..1440
            s = max(0, min(1440, s))
            e = max(0, min(1440, e))
            if e <= s:
                continue
            for minute in range(s, e):
                if minute < 1440:
                    grid[d][minute] = True
    return grid


def verify_rows_match_required(rows: List[dict], required: List[List[bool]]) -> None:
    # Build simulated grid from rows (OR semantics)
    sim = [[False] * 1440 for _ in range(7)]

    def day_enabled(r: dict, d: int) -> bool:
        return (
            (d == 0 and r["Sun"])
            or (d == 1 and r["Mon"])
            or (d == 2 and r["Tue"])
            or (d == 3 and r["Wed"])
            or (d == 4 and r["Thu"])
            or (d == 5 and r["Fri"])
            or (d == 6 and r["Sat"])
        )

    def hhmm_to_min(hhmm: str) -> int:
        h = int(hhmm[:2])
        m = int(hhmm[2:])
        return h * 60 + m

    for r in rows:
        s = r["Start"]
        e = r["End"]
        if s == "0000" and e == "0000":
            continue
        start = hhmm_to_min(s)
        end = hhmm_to_min(e)
        if end == 0:
            end = 1440  # treat 0000 end as midnight/end-of-day
        for d in range(7):
            if not day_enabled(r, d):
                continue
            for m in range(start, min(end, 1440)):
                sim[d][m] = True

    mismatches = []
    for d in range(7):
        for m in range(1440):
            if sim[d][m] != required[d][m]:
                mismatches.append((d, m, required[d][m], sim[d][m]))
                if len(mismatches) >= 20:
                    break
        if len(mismatches) >= 20:
            break

    if mismatches:
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        print("ERROR: HMS rows do not match required schedule (showing up to 20 mismatches):")
        for d, m, req, got in mismatches:
            print(f"  {day_names[d]} {m//60:02d}:{m%60:02d} required={int(req)} simulated={int(got)}")
        raise SystemExit(2)
