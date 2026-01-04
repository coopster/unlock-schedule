from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from zoneinfo import ZoneInfo
from unlock_schedule.config import (
    CALENDAR_ID,
    DAY_NAMES,
    DEFAULT_OPTIMIZE,
    DEFAULT_PAD_AFTER_MIN,
    DEFAULT_PAD_BEFORE_MIN,
    MAX_INTERVALS,
    SERVICE_ACCOUNT_FILE,
    TZ,
)


@dataclass(frozen=True)
class AppSettings:
    tz_name: str
    credentials_file: str
    calendar_id: str
    pad_before_min: int
    pad_after_min: int
    optimize: bool

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)


def load_settings() -> AppSettings:
    return AppSettings(
        tz_name=getattr(TZ, "key", str(TZ)),
        credentials_file=SERVICE_ACCOUNT_FILE,
        calendar_id=CALENDAR_ID,
        pad_before_min=DEFAULT_PAD_BEFORE_MIN,
        pad_after_min=DEFAULT_PAD_AFTER_MIN,
        optimize=DEFAULT_OPTIMIZE,
    )
