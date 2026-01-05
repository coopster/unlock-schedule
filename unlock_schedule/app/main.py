from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from unlock_schedule.app.routers.week import router as week_router
from unlock_schedule.version import get_version


def create_app() -> FastAPI:
    app = FastAPI(title="HMS Unlock Schedule")
    app.state.version = get_version()

    @app.get("/health")
    def health():
        return {"status": "ok", "version": app.state.version}

    app.include_router(week_router)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app


app = create_app()
