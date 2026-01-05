from __future__ import annotations

import os
from typing import Optional
from zoneinfo import ZoneInfo


# The calendar we use is the PSCRC "Building Access" calendar, which our service account has access to
CALENDAR_ID = os.environ.get(
    "HMS_UNLOCK_CALENDAR_ID",
    "494d928efa8c2b71c2212addcf885d61722f8d75287588b4d7ed5e0c11380b7f@group.calendar.google.com",
)

# Path to service account JSON key file: treat as secret
# export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TZ = ZoneInfo(os.environ.get("HMS_UNLOCK_TZ", "America/New_York"))

# Default padding (can be overridden via CLI / app)
DEFAULT_PAD_BEFORE_MIN = int(os.environ.get("HMS_UNLOCK_PAD_BEFORE_MIN", "0"))
DEFAULT_PAD_AFTER_MIN = int(os.environ.get("HMS_UNLOCK_PAD_AFTER_MIN", "0"))

MERGE_TOUCHING = True

# Whether to use the optimizer by default (applies to web UI).
DEFAULT_OPTIMIZE = os.environ.get("HMS_UNLOCK_OPTIMIZE", "").lower() in {"1", "true", "yes", "on"}

# Output CSV (can be overridden via CLI)
DEFAULT_OUTPUT_CSV = os.environ.get("HMS_UNLOCK_OUTPUT_CSV", "hms_unlock_schedule_template.csv")

# All CSV outputs are written under this folder (relative to project root/cwd).
OUTPUT_DIR = os.environ.get("HMS_UNLOCK_OUTPUT_DIR", "out")

# HMS supports up to 8 intervals
MAX_INTERVALS = int(os.environ.get("HMS_UNLOCK_MAX_INTERVALS", "8"))

DAY_NAMES = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")  # HMS order
