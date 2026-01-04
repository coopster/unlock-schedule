from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    sources: Tuple[str, ...]

