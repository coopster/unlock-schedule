from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Tuple

from unlock_schedule.config import (
            DAY_NAMES,
            DEFAULT_OPTIMIZE,
            DEFAULT_PAD_AFTER_MIN,
            DEFAULT_PAD_BEFORE_MIN,
            MAX_INTERVALS,
            MERGE_TOUCHING,
            TZ
        )
from unlock_schedule.core.gcal.parser import parse_event_to_interval
from unlock_schedule.core.models import Interval
from unlock_schedule.core.schedule.intervals import apply_padding, merge_intervals
from unlock_schedule.core.schedule.optimize import build_weekly_template_optimized
from unlock_schedule.core.schedule.template import build_weekly_template
from unlock_schedule.core.schedule.verify import build_required_grid, verify_rows_match_required


@dataclass(frozen=True)
class GenerateOptions:
    pad_before_min: int = DEFAULT_PAD_BEFORE_MIN
    pad_after_min: int = DEFAULT_PAD_AFTER_MIN
    optimize: bool = DEFAULT_OPTIMIZE
    day_names: Tuple[str, ...] = tuple(DAY_NAMES)
    max_intervals: int = MAX_INTERVALS
    tz: ZoneInfo = TZ


def override_options(options: GenerateOptions, /, **overrides) -> GenerateOptions:
    """
    Return a copy of `options` with specified fields overridden.

    Example:
      new_opts = override_options(opts, optimize=True, max_intervals=6)
    """
    valid_fields = {f.name for f in fields(GenerateOptions)}
    unknown = set(overrides) - valid_fields
    if unknown:
        raise ValueError(f"Unknown GenerateOptions field(s): {sorted(unknown)}")
    return replace(options, **overrides)


def generate_unlock_schedule(
    *,
    service,
    calendar_id: str,
    window_start: datetime,
    window_end: datetime,
    options: GenerateOptions,
) -> List[dict]:
    
    # Fetch events from the Calendar using the provided window
    """
    Generate an HMS "weekly template" schedule from Google Calendar events.

    This function:
    1. Fetches events from the provided Calendar using the provided window.
    2. Parses each event into an Interval (if applicable).
    3. Builds an unlock schedule that keeps the HMS open for only these events

    Returns:
        A list of dict objects, each representing a single row in the HMS schedule UI.
    """
    from unlock_schedule.core.gcal.client import fetch_events

    events = fetch_events(service, window_start, window_end, calendar_id=calendar_id)
    
    intervals = prepare_intervals(events,
        options=options,
        window_start=window_start,
        window_end=window_end
    )
    return build_unlock_rows(intervals, options=options)
    
def prepare_intervals(
    events: List[dict],
    *,
    options: GenerateOptions,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None
) -> List[Interval]:

    """
    Prepare a list of Interval objects from a list of Google Calendar events.

    This function:
    1. Parses each event into an Interval (if applicable).
    2. Merges intervals that touch if so configured.
    3. Pads intervals if so configured.
    4. Sorts intervals by start time.

    Args:
        events: A list of Google Calendar events (as dicts).
        options: GenerateOptions object containing configuration options.
        window_start: Optional[datetime] indicating the start of the window.
        window_end: Optional[datetime] indicating the end of the window.

    Returns:
        A list of Interval objects representing the unlock schedule.
    """
    if window_start and window_start.tzinfo is None:
        raise ValueError("window_start must be timezone-aware")
    
    # Parse events into intervals
    intervals: List[Interval] = []
    for e in events:
        iv = parse_event_to_interval(
            e,
            window_start,
            window_end,
            tz=options.tz,
        )
        if iv:
            intervals.append(iv)

    # Merge intervals that touch if so configured
    intervals = merge_intervals(intervals, merge_touching=MERGE_TOUCHING)

    if intervals and (window_start is None or window_end is None):
        min_start = min(iv.start for iv in intervals)
        max_end = max(iv.end for iv in intervals)
        window_start = window_start or (min_start - timedelta(days=1))
        window_end = window_end or (max_end + timedelta(days=1))

    # Pad intervals if so configured
    if options.pad_before_min or options.pad_after_min:
        intervals = [
            apply_padding(iv, options.pad_before_min, options.pad_after_min, window_start, window_end) for iv in intervals  # type: ignore[arg-type]
        ]
        intervals = merge_intervals(intervals, merge_touching=MERGE_TOUCHING)
    
    # Sort intervals by start time and return the list of intervals
    return sorted(intervals, key=lambda iv: iv.start)


def build_unlock_rows(intervals: List[Interval], *, options: GenerateOptions) -> List[dict]:
    """
    Builds the HMS unlock schedule rows from a list of intervals.

    If options.optimize is False, build the rows using the non-optimized
    build_weekly_template function. If the resulting number of rows exceeds
    options.max_intervals, log a message and retry with optimized set to True.

    Otherwise, build the rows using the optimized build_weekly_template_optimized
    function.

    Verify that the resulting rows match the required grid.

    Returns:
        A list of dictionaries, where each dictionary represents a row in the HMS
        unlock schedule template.
    """
    if not options.optimize:
        rows = build_weekly_template(intervals, day_names=options.day_names, max_intervals=options.max_intervals)
        if (len(rows) > options.max_intervals):
            # Rerun with optimized turned on in an attempt to reduce the number of distinct intervals needed
            # Log that we needed to try optimized to get the right number of intervals
            print(f"INFO: Need to optimize to get the right number of intervals after calculating {len(rows)} intervals")
            rows = build_weekly_template_optimized(intervals, max_intervals=options.max_intervals)
    else:
        rows = build_weekly_template_optimized(intervals, max_intervals=options.max_intervals)

    # Verify that the rows match the required grid
    required = build_required_grid(intervals)
    verify_rows_match_required(rows, required)

    return rows
