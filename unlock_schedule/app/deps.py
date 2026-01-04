from __future__ import annotations

from functools import lru_cache

from unlock_schedule.app.settings import AppSettings, load_settings


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()
