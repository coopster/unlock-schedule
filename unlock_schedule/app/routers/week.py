from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from unlock_schedule.app.deps import get_settings
from unlock_schedule.app.settings import AppSettings
from unlock_schedule.config import DAY_NAMES, MAX_INTERVALS
from unlock_schedule.core.gcal.client import build_calendar_service
from unlock_schedule.core.service import GenerateOptions, generate_unlock_schedule
from unlock_schedule.core.window import week_window_from_date


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _default_start_date(settings: AppSettings) -> date:
    return datetime.now(tz=settings.tz).date()


@router.get("/", response_class=HTMLResponse)
def week_page(
    request: Request,
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    selected_date = start_date or _default_start_date(settings)
    window_start, window_end = week_window_from_date(selected_date, settings.tz)

    error = None
    rows = []
    try:
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
    except SystemExit as e:
        error = str(e)

    return templates.TemplateResponse(
        request,
        "week.html",
        {
            "start_date": selected_date.isoformat(),
            "window_start": window_start,
            "window_end": window_end,
            "rows": rows,
            "day_names": DAY_NAMES,
            "error": error,
        },
    )


@router.get("/api/week")
def week_api(
    start_date: Optional[date] = Query(default=None),
    settings: AppSettings = Depends(get_settings),
):
    selected_date = start_date or _default_start_date(settings)
    window_start, window_end = week_window_from_date(selected_date, settings.tz)

    try:
        service = build_calendar_service(settings.credentials_file)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    options = GenerateOptions(
        pad_before_min=settings.pad_before_min,
        pad_after_min=settings.pad_after_min,
        optimize=settings.optimize,
        day_names=DAY_NAMES,
        max_intervals=MAX_INTERVALS,
    )
    try:
        rows = generate_unlock_schedule(
            service=service,
            calendar_id=settings.calendar_id,
            window_start=window_start,
            window_end=window_end,
            options=options,
        )
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "start_date": selected_date.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows": rows,
    }
