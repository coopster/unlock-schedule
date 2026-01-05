from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from unlock_schedule.app.deps import get_settings
from unlock_schedule.app.settings import AppSettings
from unlock_schedule.config import DAY_NAMES, MAX_INTERVALS
from unlock_schedule.core.gcal.client import build_calendar_service
from unlock_schedule.core.io.csv_writer import rows_to_hms_csv
from unlock_schedule.core.service import GenerateOptions, generate_unlock_schedule
from unlock_schedule.core.window import week_window_from_date


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _default_start_date(settings: AppSettings) -> date:
    return datetime.now(tz=settings.tz).date()


def _generate_payload(*, selected_date: date, settings: AppSettings) -> dict:
    window_start, window_end = week_window_from_date(selected_date, settings.tz)
    service = build_calendar_service(settings.credentials_file)
    options = GenerateOptions(
        pad_before_min=settings.pad_before_min,
        pad_after_min=settings.pad_after_min,
        optimize=settings.optimize,
        day_names=DAY_NAMES,
        max_intervals=MAX_INTERVALS,
    )
    rows = generate_unlock_schedule(
        service=service,
        calendar_id=settings.calendar_id,
        window_start=window_start,
        window_end=window_end,
        options=options,
    )
    return {
        "start_date": selected_date.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows": rows,
    }


@router.get("/", response_class=HTMLResponse)
def week_page(
    request: Request,
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    today = _default_start_date(settings)
    selected_date = start_date or today
    error = None
    rows = []
    window_start = None
    window_end = None
    window_label = None
    try:
        payload = _generate_payload(selected_date=selected_date, settings=settings)
        rows = payload["rows"]
        window_start = datetime.fromisoformat(payload["window_start"])
        window_end = datetime.fromisoformat(payload["window_end"])
    except SystemExit as e:
        error = str(e)
        window_start, window_end = week_window_from_date(selected_date, settings.tz)

    if window_start and window_end:
        inclusive_end = (window_end - timedelta(days=1)).date()
        window_label = f"{window_start.strftime('%a %m/%d/%y')} – {inclusive_end.strftime('%a %m/%d/%y')}"

    return templates.TemplateResponse(
        request,
        "week.html",
        {
            "today": today.isoformat(),
            "start_date": selected_date.isoformat(),
            "window_start": window_start,
            "window_end": window_end,
            "window_label": window_label,
            "rows": rows,
            "day_names": DAY_NAMES,
            "error": error,
            "version": getattr(request.app.state, "version", ""),
        },
    )


@router.get("/api/week")
def week_api(
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    selected_date = start_date or _default_start_date(settings)
    try:
        return _generate_payload(selected_date=selected_date, settings=settings)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/download/week.csv")
def week_csv_download(
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    selected_date = start_date or _default_start_date(settings)
    try:
        payload = _generate_payload(selected_date=selected_date, settings=settings)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    csv_text = rows_to_hms_csv(payload["rows"])
    filename = f"unlock_schedule_{payload['start_date']}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/week.json")
def week_json_download(
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    selected_date = start_date or _default_start_date(settings)
    try:
        payload = _generate_payload(selected_date=selected_date, settings=settings)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    filename = f"unlock_schedule_{payload['start_date']}.json"
    return Response(
        content=json.dumps(payload, indent=2, sort_keys=True),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
