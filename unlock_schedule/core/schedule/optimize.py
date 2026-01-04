from __future__ import annotations

from typing import List, Tuple
from unlock_schedule.core.models import Interval
from unlock_schedule.core.schedule.verify import build_required_grid


def min_to_hhmm(m: int) -> str:
    # Allow 1440 to represent end-of-day; HMS often accepts 0000 as "midnight/end"
    if m == 1440:
        return "0000"
    h = m // 60
    mm = m % 60
    return f"{h:02d}{mm:02d}"


def _run_boundary_sets(grid: List[List[bool]]) -> tuple[list[set[int]], list[set[int]]]:
    """
    Return (run_starts, run_ends) where:
    - run_starts[d] contains minute offsets where a required run starts on day d.
    - run_ends[d] contains minute offsets where a required run ends on day d (end minute, in 1..1440).
    """
    run_starts: list[set[int]] = [set() for _ in range(7)]
    run_ends: list[set[int]] = [set() for _ in range(7)]

    for d in range(7):
        in_run = False
        start = 0
        for m in range(1440):
            if grid[d][m] and not in_run:
                in_run = True
                start = m
            if in_run and (m == 1439 or not grid[d][m + 1]):
                run_starts[d].add(start)
                run_ends[d].add(m + 1)
                in_run = False
    return run_starts, run_ends


def extract_boundaries_from_grid(grid: List[List[bool]]) -> List[int]:
    """
    Get all start/end boundaries across all days as minute offsets [0..1440].
    """
    boundaries = {0, 1440}
    for d in range(7):
        in_run = False
        run_start = 0
        for m in range(1440):
            if grid[d][m] and not in_run:
                in_run = True
                run_start = m
            if in_run and (m == 1439 or not grid[d][m + 1]):
                boundaries.add(run_start)
                boundaries.add(m + 1)
                in_run = False
    return sorted(boundaries)


def candidate_intervals(boundaries: List[int]) -> List[Tuple[int, int]]:
    """
    All candidate time intervals from boundaries: (start_min, end_min).
    """
    cands = []
    n = len(boundaries)
    for i in range(n):
        for j in range(i + 1, n):
            s = boundaries[i]
            e = boundaries[j]
            if e > s:
                cands.append((s, e))
    cands.sort(key=lambda x: (-(x[1] - x[0]), x[0], x[1]))
    return cands


def build_weekly_template_optimized(intervals: List[Interval], *, max_intervals: int) -> List[dict]:
    """
    Greedy cover optimizer that NEVER adds unlock time:
    A candidate time window (s,e) can be enabled for a day d only if
    required[d][m] is True for ALL minutes m in [s,e).

    Assumes HMS state is OR of enabled intervals.
    """
    grid = build_required_grid(intervals)
    run_starts, run_ends = _run_boundary_sets(grid)

    remaining = set()
    for d in range(7):
        for m in range(1440):
            if grid[d][m]:
                remaining.add((d, m))

    if not remaining:
        return [
            {
                "Interval": i,
                "Start": "0000",
                "End": "0000",
                "Sun": 0,
                "Mon": 0,
                "Tue": 0,
                "Wed": 0,
                "Thu": 0,
                "Fri": 0,
                "Sat": 0,
                "Holidays": 0,
            }
            for i in range(1, max_intervals + 1)
        ]

    boundaries = extract_boundaries_from_grid(grid)
    cands = candidate_intervals(boundaries)

    def day_is_fully_covered(d: int, s: int, e: int) -> bool:
        upper = min(e, 1440)
        for m in range(s, upper):
            if not grid[d][m]:
                return False
        return True

    chosen: List[Tuple[int, int, set[int]]] = []

    while remaining:
        best_s = best_e = None
        best_days: set[int] = set()
        best_cover: set[Tuple[int, int]] = set()
        best_alignment = -1

        for (s, e) in cands:
            if e <= s:
                continue

            eligible_days = {d for d in range(7) if day_is_fully_covered(d, s, e)}
            if not eligible_days:
                continue

            cover = set()
            contributing_days: set[int] = set()
            upper = min(e, 1440)
            for d in eligible_days:
                for m in range(s, upper):
                    if (d, m) in remaining:
                        cover.add((d, m))
                        contributing_days.add(d)

            if not cover:
                continue

            alignment = 0
            for d in contributing_days:
                if s in run_starts[d]:
                    alignment += 1
                if e in run_ends[d]:
                    alignment += 1

            if best_s is None:
                best_s, best_e = s, e
                best_days = contributing_days
                best_cover = cover
                best_alignment = alignment
                continue

            score = (alignment, len(cover), (e - s), -s)
            best_score = (best_alignment, len(best_cover), (best_e - best_s), -best_s)  # type: ignore[operator]
            if score > best_score:
                best_s, best_e = s, e
                best_days = contributing_days
                best_cover = cover
                best_alignment = alignment

        if best_s is None or best_e is None:
            raise SystemExit(
                "ERROR: Optimizer couldn't find any safe interval to cover remaining required minutes.\n"
                "This usually means the boundary generation logic missed needed edges."
            )

        chosen.append((best_s, best_e, best_days))
        remaining -= best_cover

        if len(chosen) > max_intervals:
            raise SystemExit(
                f"ERROR: Need more than {max_intervals} HMS intervals even after optimization.\n"
                f"Tip: Standardize times or reduce variability."
            )

    rows: List[dict] = []
    for idx, (s, e, days_on) in enumerate(chosen, start=1):
        rows.append(
            {
                "Interval": idx,
                "Start": min_to_hhmm(s),
                "End": min_to_hhmm(e),
                "Sun": 1 if 0 in days_on else 0,
                "Mon": 1 if 1 in days_on else 0,
                "Tue": 1 if 2 in days_on else 0,
                "Wed": 1 if 3 in days_on else 0,
                "Thu": 1 if 4 in days_on else 0,
                "Fri": 1 if 5 in days_on else 0,
                "Sat": 1 if 6 in days_on else 0,
                "Holidays": 0,
            }
        )

    rows_sorted = sorted(rows, key=lambda r: (r["Start"], r["End"]))
    for i, r in enumerate(rows_sorted, start=1):
        r["Interval"] = i
    rows = rows_sorted

    while len(rows) < max_intervals:
        idx = len(rows) + 1
        rows.append(
            {
                "Interval": idx,
                "Start": "0000",
                "End": "0000",
                "Sun": 0,
                "Mon": 0,
                "Tue": 0,
                "Wed": 0,
                "Thu": 0,
                "Fri": 0,
                "Sat": 0,
                "Holidays": 0,
            }
        )

    return rows
