"""FastAPI app that serves the daily leadership-jobs digest.

Runs APScheduler in-process: every day at 09:00 (server local time) it calls
`scrape_all()` to refresh the database, then any page load reflects the latest
state.

Endpoints:
    GET  /            -> HTML digest, grouped by platform
    GET  /today       -> HTML digest, only jobs found today
    POST /refresh     -> manually trigger a scrape (returns JSON summary)
    GET  /healthz     -> JSON liveness probe with last-run info
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from platforms import PLATFORMS
from scraper import get_jobs_grouped, get_last_run, scrape_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("app")

templates = Jinja2Templates(directory="templates")
scheduler = AsyncIOScheduler()


async def scheduled_job() -> None:
    log.info("Starting scheduled scrape (09:00 daily)")
    try:
        results, total_new = await scrape_all()
        log.info("Scheduled scrape complete: %d new jobs across %d platforms", total_new, len(results))
    except Exception:
        log.exception("Scheduled scrape failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=9, minute=0),
        id="daily_scrape",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    log.info("Scheduler started; daily scrape registered for 09:00")
    last = get_last_run()
    if last is None:
        log.info("No previous run found, kicking off initial scrape in background")
        asyncio.create_task(scheduled_job())
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Leadership Jobs Digest", lifespan=lifespan)


def _render(request: Request, only_today: bool) -> HTMLResponse:
    grouped = get_jobs_grouped(only_today=only_today)
    new_count = sum(len(v) for v in grouped.values())
    last = get_last_run()
    last_str = (
        last.finished_at.strftime("%Y-%m-%d %H:%M UTC") if last and last.finished_at
        else "never"
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "jobs": grouped,
            "update_date": last_str,
            "new_count": new_count,
            "today": _dt.date.today().isoformat(),
            "only_today": only_today,
            "platforms_total": len(PLATFORMS),
        },
    )


@app.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    return _render(request, only_today=False)


@app.get("/today", response_class=HTMLResponse)
def today(request: Request) -> HTMLResponse:
    return _render(request, only_today=True)


@app.post("/refresh")
async def refresh() -> JSONResponse:
    log.info("Manual refresh triggered")
    results, total_new = await scrape_all()
    return JSONResponse({
        "total_new": total_new,
        "platforms": [
            {
                "platform": r.platform,
                "total_fetched": r.total_fetched,
                "matches": r.matches,
                "new": r.new,
                "error": r.error,
            }
            for r in results
        ],
    })


@app.get("/healthz")
def healthz() -> JSONResponse:
    last = get_last_run()
    return JSONResponse({
        "ok": True,
        "platforms_configured": len(PLATFORMS),
        "last_run_started": last.started_at.isoformat() if last else None,
        "last_run_finished": last.finished_at.isoformat() if last and last.finished_at else None,
        "last_run_new_jobs": last.new_jobs if last else None,
    })
