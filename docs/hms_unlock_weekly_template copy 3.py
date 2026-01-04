#!/usr/bin/env python3
"""
hms_unlock_weekly_template.py

Fetch a week's worth of Google Calendar events from the PSCRC "Building Access"
calendar using a service account, convert them into HMS "weekly template"
intervals (up to 8), and write a CSV matching the HMS schedule UI.

NEW: Optional command-line argument --start-date to test historical weeks.
- The requested window is the full 24-hour period starting on that date (00:00 local)
  and the following 6 days (total 7 days): [start, start+7days).
- If --start-date is omitted, the window is "next week starting Sunday".

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
  python hms_unlock_weekly_template.py
  python hms_unlock_weekly_template.py --start-date 2025-12-07
  python hms_unlock_weekly_template.py --start-date 2025-12-07 --pad-before 15 --pad-after 15
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ----------------------------
# Configuration
# ----------------------------

CALENDAR_ID = "494d928efa8c2b71c2212addcf885d61722f8d75287588b4d7ed5e0c11380b7f@group.calendar.google.com"

# Path to service account JSON key file:
# export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TZ = ZoneInfo("America/New_York")

# Default padding (can be overridden via CLI)
DEFAULT_PAD_BEFORE_MIN = 0
DEFAULT_PAD_AFTER_MIN = 0

# All-day events are dangerous for door schedules; default ignore.
DEFAULT_INCLUDE_ALL_DAY_EVENTS = False

# Optional: only include events with title prefix, e.g. "UNLOCK:"
DEFAULT_TITLE_PREFIX_FILTER: Optional[str] = None

# Merge policy: touching intervals merge (end == start).
DEFAULT_MERGE_TOUCHING = True

# Output CSV (can be overridden via CLI)
DEFAULT_OUTPUT_CSV = "hms_unlock_schedule_template_next_week.csv"

# HMS supports up to 8 intervals
MAX_INTERVALS = 8

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # HMS order


# ----------------------------
# Data types
# ----------------------------

@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    sources: Tuple[str, ...]


# ----------------------------
# Window helpers
# ----------------------------

def next_sunday_midnight(now: datetime) -> datetime:
    """Next Sunday 00:00 in same timezone. If today is Sunday, returns today's midnight."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    # weekday(): Mon=0 .. Sun=6
    days_ahead = (6 - now.weekday()) % 7
    start_date = (now + timedelta(days=days_ahead)).date()
    return datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=now.tzinfo)


def week_window_starting_sunday(now: datetime) -> Tuple[datetime, datetime]:
    start = next_sunday_midnight(now)
    end = start + timedelta(days=7)
    return start, end


def week_window_from_date(start_d: date, tz: ZoneInfo) -> Tuple[datetime, datetime]:
    """
    Return [start, start+7days) where start is local midnight at start_d.
    This includes the full 24-hour period starting on start_d and the following 6 days.
    """
    start = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=tz)
    end = start + timedelta(days=7)
    return start, end


# ----------------------------
# Google Calendar auth + fetch
# ----------------------------

def build_calendar_service(service_account_file: str):
    if not service_account_file:
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON key path.\n"
            "Example:\n"
            "  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json"
        )

    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_events(service, time_min: datetime, time_max: datetime) -> List[dict]:
    events: List[dict] = []
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


# ----------------------------
# Event -> Interval parsing
# ----------------------------

def parse_event_to_interval(
    e: dict,
    window_start: datetime,
    window_end: datetime,
    *,
    include_all_day_events: bool,
    title_prefix_filter: Optional[str],
) -> Optional[Interval]:
    summary = e.get("summary", "(no title)")

    if title_prefix_filter and not summary.startswith(title_prefix_filter):
        return None

    start_obj = e.get("start", {})
    end_obj = e.get("end", {})

    # Timed event
    if "dateTime" in start_obj and "dateTime" in end_obj:
        start = datetime.fromisoformat(start_obj["dateTime"]).astimezone(TZ)
        end = datetime.fromisoformat(end_obj["dateTime"]).astimezone(TZ)

    # All-day event
    elif "date" in start_obj and "date" in end_obj:
        if not include_all_day_events:
            return None
        start_date = datetime.fromisoformat(start_obj["date"]).date()
        end_date = datetime.fromisoformat(end_obj["date"]).date()  # usually next day
        start = datetime.combine(start_date, time(0, 0), tzinfo=TZ)
        end = datetime.combine(end_date, time(0, 0), tzinfo=TZ)

    else:
        return None

    if end <= start:
        return None

    # Clamp to window
    start = max(start, window_start)
    end = min(end, window_end)
    if end <= start:
        return None

    return Interval(start=start, end=end, sources=(summary,))


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
    after_min: int,
    window_start: datetime,
    window_end: datetime,
) -> Interval:
    start = interval.start - timedelta(minutes=before_min)
    end = interval.end + timedelta(minutes=after_min)
    start = max(start, window_start)
    end = min(end, window_end)
    return Interval(start=start, end=end, sources=interval.sources)


# ----------------------------
# Split intervals by day (because HMS toggles per day)
# ----------------------------

def split_interval_by_day(iv: Interval) -> List[Interval]:
    """
    Split an interval at midnight boundaries into per-day segments.
    Returns segments each contained within a single calendar day.
    """
    segments: List[Interval] = []
    cur_start = iv.start
    cur_end = iv.end

    while cur_start.date() < cur_end.date():
        next_midnight = datetime.combine(cur_start.date() + timedelta(days=1), time(0, 0), tzinfo=TZ)
        segments.append(Interval(start=cur_start, end=next_midnight, sources=iv.sources))
        cur_start = next_midnight

    segments.append(Interval(start=cur_start, end=cur_end, sources=iv.sources))
    return segments


def to_hhmm(dt: datetime) -> str:
    return dt.strftime("%H%M")


def hms_day_index(dt: datetime) -> int:
    """
    Convert dt to HMS day index: Sun=0..Sat=6.
    Python weekday: Mon=0..Sun=6
    """
    py = dt.weekday()
    return (py + 1) % 7  # Mon->1 ... Sat->6, Sun->0


# ----------------------------
# Build HMS template rows
# ----------------------------

def build_weekly_template(intervals: List[Interval], max_intervals: int = MAX_INTERVALS) -> List[dict]:
    """
    Group intervals by identical (startHHMM, endHHMM), set day flags.
    Returns exactly max_intervals rows (pads unused with 0000,0000 and no days selected).
    """
    grouped: Dict[Tuple[str, str], Dict[str, int]] = {}

    for iv in intervals:
        for seg in split_interval_by_day(iv):
            start_h = to_hhmm(seg.start)
            end_h = to_hhmm(seg.end)

            if start_h == end_h:
                continue

            key = (start_h, end_h)
            if key not in grouped:
                grouped[key] = {d: 0 for d in DAY_NAMES}
                grouped[key]["Holidays"] = 0

            day_idx = hms_day_index(seg.start)
            grouped[key][DAY_NAMES[day_idx]] = 1

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
        rows.append({
            "Interval": i,
            "Start": start_h,
            "End": end_h,
            "Sun": grouped[k]["Sun"],
            "Mon": grouped[k]["Mon"],
            "Tue": grouped[k]["Tue"],
            "Wed": grouped[k]["Wed"],
            "Thu": grouped[k]["Thu"],
            "Fri": grouped[k]["Fri"],
            "Sat": grouped[k]["Sat"],
            "Holidays": grouped[k]["Holidays"],
        })

    while len(rows) < max_intervals:
        idx = len(rows) + 1
        rows.append({
            "Interval": idx,
            "Start": "0000",
            "End": "0000",
            "Sun": 0, "Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0,
            "Holidays": 0,
        })

    return rows


# ----------------------------
# Build HMS template rows optimized to minimize the number of intervals through interval decomposition
# ----------------------------


def hhmm_to_min(hhmm: str) -> int:
    h = int(hhmm[:2])
    m = int(hhmm[2:])
    return h * 60 + m

def min_to_hhmm(m: int) -> str:
    # Allow 1440 to represent end-of-day; HMS often accepts 0000 as "midnight/end"
    if m == 1440:
        return "0000"
    h = m // 60
    mm = m % 60
    return f"{h:02d}{mm:02d}"

def interval_minutes(iv: Interval) -> Tuple[int, int]:
    return (iv.start.hour * 60 + iv.start.minute, iv.end.hour * 60 + iv.end.minute)

def build_required_grid(intervals: List[Interval]) -> List[List[bool]]:
    """
    Returns grid[day][minute] = True if unlocked at that minute for that day.
    day index: 0=Sun..6=Sat
    minute: 0..1439
    """
    grid = [[False] * 1440 for _ in range(7)]

    for iv in intervals:
        for seg in split_interval_by_day(iv):
            d = hms_day_index(seg.start)
            s, e = interval_minutes(seg)
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
                # run ends at m+1
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
    # Prefer longer intervals first (greedy cover benefit)
    cands.sort(key=lambda x: (-(x[1] - x[0]), x[0], x[1]))
    return cands

def covered_minutes_for_candidate(
    grid: List[List[bool]],
    s: int,
    e: int,
    day: int
) -> List[int]:
    """
    Return list of minute indices that candidate (s,e) would unlock on 'day',
    but only where unlock is actually required.
    """
    mins = []
    upper = min(e, 1440)
    for m in range(s, upper):
        if grid[day][m]:
            mins.append(m)
    return mins

def build_weekly_template_optimized(intervals: List[Interval], max_intervals: int = MAX_INTERVALS) -> List[dict]:
    """
    Greedy cover optimizer that NEVER adds unlock time:
    A candidate time window (s,e) can be enabled for a day d only if
    required[d][m] is True for ALL minutes m in [s,e).

    Assumes HMS state is OR of enabled intervals.
    """
    grid = build_required_grid(intervals)

    # Universe: all required (day, minute)
    remaining = set()
    for d in range(7):
        for m in range(1440):
            if grid[d][m]:
                remaining.add((d, m))

    if not remaining:
        rows = []
        for i in range(1, max_intervals + 1):
            rows.append({
                "Interval": i, "Start": "0000", "End": "0000",
                "Sun": 0, "Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0,
                "Holidays": 0,
            })
        return rows

    boundaries = extract_boundaries_from_grid(grid)
    cands = candidate_intervals(boundaries)

    def day_is_fully_covered(d: int, s: int, e: int) -> bool:
        """True iff every minute in [s,e) is required on day d."""
        upper = min(e, 1440)
        for m in range(s, upper):
            if not grid[d][m]:
                return False
        return True

    chosen: List[Tuple[int, int, set[int]]] = []

    # Greedy loop
    while remaining:
        best_s = best_e = None
        best_days: set[int] = set()
        best_cover: set[Tuple[int, int]] = set()

        for (s, e) in cands:
            if e <= s:
                continue

            # Eligible days are those where the entire interval is required.
            eligible_days = {d for d in range(7) if day_is_fully_covered(d, s, e)}
            if not eligible_days:
                continue

            cover = set()
            upper = min(e, 1440)
            for d in eligible_days:
                for m in range(s, upper):
                    if (d, m) in remaining:
                        cover.add((d, m))

            if not cover:
                continue

            # Score: cover most remaining; then prefer longer intervals (fewer total); then earlier start
            score = (len(cover), (e - s), -s)

            if len(cover) > len(best_cover) or (
                len(cover) == len(best_cover) and best_s is not None and score > (len(best_cover), (best_e - best_s), -best_s)  # type: ignore
            ) or best_s is None:
                best_s, best_e = s, e
                best_days = eligible_days
                best_cover = cover

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

    # Convert chosen intervals into HMS rows
    rows: List[dict] = []
    for idx, (s, e, days_on) in enumerate(chosen, start=1):
        rows.append({
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
        })

    # Sort for nicer viewing
    rows_sorted = sorted(rows, key=lambda r: (r["Start"], r["End"]))
    for i, r in enumerate(rows_sorted, start=1):
        r["Interval"] = i
    rows = rows_sorted

    # Pad to exactly 8
    while len(rows) < max_intervals:
        idx = len(rows) + 1
        rows.append({
            "Interval": idx,
            "Start": "0000",
            "End": "0000",
            "Sun": 0, "Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0,
            "Holidays": 0,
        })

    return rows

# ----------------------------
# Verify rows match required
# ----------------------------

def verify_rows_match_required(rows: List[dict], required: List[List[bool]]) -> None:
    # Build simulated grid from rows (OR semantics)
    sim = [[False] * 1440 for _ in range(7)]

    def day_enabled(r: dict, d: int) -> bool:
        return (
            (d == 0 and r["Sun"]) or
            (d == 1 and r["Mon"]) or
            (d == 2 and r["Tue"]) or
            (d == 3 and r["Wed"]) or
            (d == 4 and r["Thu"]) or
            (d == 5 and r["Fri"]) or
            (d == 6 and r["Sat"])
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

    # Compare
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
        # Show a small sample
        day_names = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        print("ERROR: HMS rows do not match required schedule (showing up to 20 mismatches):")
        for d, m, req, got in mismatches:
            print(f"  {day_names[d]} {m//60:02d}:{m%60:02d} required={int(req)} simulated={int(got)}")
        raise SystemExit(2)

# ----------------------------
# Output
# ----------------------------

def write_hms_csv(rows: List[dict], path: str) -> None:
    fieldnames = ["Interval", "Start", "End", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Holidays"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ----------------------------
# CLI + main
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate HMS unlock schedule CSV from Google Calendar.")
    p.add_argument(
        "--start-date",
        help="Start date for 7-day window in YYYY-MM-DD (local time). If omitted, uses next week starting Sunday.",
        default=None,
    )
    p.add_argument("--pad-before", type=int, default=DEFAULT_PAD_BEFORE_MIN, help="Minutes to unlock early (default: 0).")
    p.add_argument("--pad-after", type=int, default=DEFAULT_PAD_AFTER_MIN, help="Minutes to relock late (default: 0).")
    p.add_argument(
        "--include-all-day",
        action="store_true",
        default=DEFAULT_INCLUDE_ALL_DAY_EVENTS,
        help="Include all-day events (default: off).",
    )
    p.add_argument(
        "--title-prefix",
        default=DEFAULT_TITLE_PREFIX_FILTER,
        help='Only include events whose title starts with this prefix (e.g., "UNLOCK:").',
    )
    p.add_argument(
        "--no-merge-touching",
        action="store_true",
        help="Do NOT merge intervals that touch exactly at boundaries (default merges touching).",
    )
    p.add_argument(
        "--optimize",
        action="store_true",
        help="Use optimized interval decomposition to minimize number of HMS intervals.",
    )
    p.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV}).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    now = datetime.now(tz=TZ)

    if args.start_date:
        try:
            start_d = date.fromisoformat(args.start_date)
        except ValueError as e:
            raise SystemExit(f"--start-date must be YYYY-MM-DD (got {args.start_date!r})") from e
        window_start, window_end = week_window_from_date(start_d, TZ)
    else:
        window_start, window_end = week_window_starting_sunday(now)

    merge_touching = not args.no_merge_touching

    service = build_calendar_service(SERVICE_ACCOUNT_FILE)
    events = fetch_events(service, window_start, window_end)

    intervals: List[Interval] = []
    for e in events:
        iv = parse_event_to_interval(
            e,
            window_start,
            window_end,
            include_all_day_events=args.include_all_day,
            title_prefix_filter=args.title_prefix,
        )
        if iv:
            intervals.append(iv)

    intervals = merge_intervals(intervals, merge_touching=merge_touching)

    if args.pad_before or args.pad_after:
        intervals = [apply_padding(iv, args.pad_before, args.pad_after, window_start, window_end) for iv in intervals]
        intervals = merge_intervals(intervals, merge_touching=merge_touching)

    # Build the HMS template    
    if args.optimize:
        rows = build_weekly_template_optimized(intervals, max_intervals=MAX_INTERVALS)
    else:
        rows = build_weekly_template(intervals, max_intervals=MAX_INTERVALS)
    
    # Verify output is correct by comparing to required schedule    
    required = build_required_grid(intervals)
    verify_rows_match_required(rows, required)
    
    # Output verified solution   
    write_hms_csv(rows, args.output)

    print(f"Window: {window_start.isoformat()} -> {window_end.isoformat()}")
    print(f"Calendar: {CALENDAR_ID}")
    print(f"Wrote: {args.output}")
    print()
    for r in rows:
        days = "".join([d if r[d] else "-" for d in DAY_NAMES])
        print(f"Interval {r['Interval']}: {r['Start']}–{r['End']}  {days}  Holidays:{r['Holidays']}")


if __name__ == "__main__":
    main()