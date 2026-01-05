from __future__ import annotations

import os

__version__ = "0.1.0"


def get_version() -> str:
    """
    Return the running app version.

    Prefer an environment-provided value (useful for Docker build args / deployments),
    otherwise fall back to the package default.
    """
    return os.getenv("UNLOCK_SCHEDULE_VERSION") or os.getenv("APP_VERSION") or __version__

