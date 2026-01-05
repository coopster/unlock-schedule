from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import List

from unlock_schedule.config import OUTPUT_DIR


HMS_CSV_FIELDNAMES = ["Interval", "Start", "End", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Holidays"]


def resolve_output_path(path: str) -> Path:
    """
    Ignore any folder components in `path` and write only by filename into OUTPUT_DIR.
    Example: "foo/bar.csv" -> "out/bar.csv"
    """
    filename = Path(path).name
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def rows_to_hms_csv(rows: List[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HMS_CSV_FIELDNAMES)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_hms_csv(rows: List[dict], path: str) -> Path:
    out_path = resolve_output_path(path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HMS_CSV_FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out_path
