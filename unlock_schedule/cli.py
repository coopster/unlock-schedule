from __future__ import annotations

import argparse
from datetime import date, datetime

from unlock_schedule.config import (
    CALENDAR_ID,
    DAY_NAMES,
    DEFAULT_OUTPUT_CSV,
    DEFAULT_PAD_AFTER_MIN,
    DEFAULT_PAD_BEFORE_MIN,
    MAX_INTERVALS,
    SERVICE_ACCOUNT_FILE,
    TZ,
)
from unlock_schedule.core.gcal.client import build_calendar_service
from unlock_schedule.core.window import week_window_from_date
from unlock_schedule.core.service import GenerateOptions, generate_unlock_schedule
from unlock_schedule.core.io.csv_writer import write_hms_csv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate HMS unlock schedule CSV from Google Calendar.")
    p.add_argument(
        "--start-date",
        help="Start date for 7-day window in YYYY-MM-DD (local time). If omitted, uses today.",
        default=None,
    )
    p.add_argument("--pad-before", type=int, default=DEFAULT_PAD_BEFORE_MIN, help="Minutes to unlock early (default: 0).")
    p.add_argument("--pad-after", type=int, default=DEFAULT_PAD_AFTER_MIN, help="Minutes to relock late (default: 0).")
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
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    now = datetime.now(tz=TZ)

    if args.start_date:
        try:
            start_d = date.fromisoformat(args.start_date)
        except ValueError as e:
            raise SystemExit(f"--start-date must be YYYY-MM-DD (got {args.start_date!r})") from e
        window_start, window_end = week_window_from_date(start_d, TZ)
    else:
        window_start, window_end = week_window_from_date(now.date(), TZ)

    options = GenerateOptions(
        pad_before_min=args.pad_before,
        pad_after_min=args.pad_after,
        optimize=args.optimize,
        day_names=DAY_NAMES,
        max_intervals=MAX_INTERVALS,
    )

    service = build_calendar_service(SERVICE_ACCOUNT_FILE)
    rows = generate_unlock_schedule(
        service=service,
        calendar_id=CALENDAR_ID,
        window_start=window_start,
        window_end=window_end,
        options=options,
    )

    out_path = write_hms_csv(rows, args.output)

    print(f"Window: {window_start.isoformat()} -> {window_end.isoformat()}")
    print(f"Wrote: {out_path}")
    print()
    for r in rows:
        days = "".join([d if r[d] else "-" for d in DAY_NAMES])
        print(f"Interval {r['Interval']}: {r['Start']}–{r['End']}  {days}  Holidays:{r['Holidays']}")


if __name__ == "__main__":
    main()
