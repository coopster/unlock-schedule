from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build

from unlock_schedule.config import CALENDAR_ID, SCOPES


def build_calendar_service(service_account_file: str):
    if not service_account_file:
        raise SystemExit(
            "Set GCAL_SERVICE_ACCOUNT_JSON to your service account JSON key path.\n"
            "Example:\n"
            "  export GCAL_SERVICE_ACCOUNT_JSON=/path/to/key.json"
        )

    key_path = Path(service_account_file).expanduser()
    if not key_path.exists():
        raise SystemExit(
            "Service account credentials path points to a file that does not exist.\n"
            f"Got: {service_account_file}\n"
            "Fix:\n"
            "  export GCAL_SERVICE_ACCOUNT_JSON=/absolute/path/to/service-account-key.json"
        )
    if not key_path.is_file():
        raise SystemExit(
            "Credentials path must point to a JSON key file.\n"
            f"Got: {service_account_file}"
        )

    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_events(service, time_min: datetime, time_max: datetime, *, calendar_id: str = CALENDAR_ID) -> List[dict]:
    events: List[dict] = []
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
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
