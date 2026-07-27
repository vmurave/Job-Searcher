"""Orchestrator: runs every platform adapter, filters by leadership keywords,
deduplicates against the DB, and records the run in `run_log`.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
from dataclasses import dataclass

from db import Job, RunLog, SessionLocal
from keywords import is_leadership_title
from platforms import PLATFORMS, JobPosting, PlatformAdapter, PlatformError

log = logging.getLogger("scraper")
PLATFORM_TIMEOUT_S = 120


@dataclass
class PlatformResult:
    platform: str
    total_fetched: int
    matches: int
    new: int
    error: str | None = None


async def _run_one(adapter: PlatformAdapter) -> tuple[PlatformAdapter, list[JobPosting] | Exception]:
    try:
        jobs = await asyncio.wait_for(adapter.fetch(), timeout=PLATFORM_TIMEOUT_S)
        return adapter, jobs
    except (asyncio.TimeoutError, PlatformError, Exception) as e:
        return adapter, e


async def scrape_all() -> tuple[list[PlatformResult], int]:
    """Run every adapter concurrently. Returns (per-platform results, total new)."""
    started = _dt.datetime.utcnow()
    results: list[PlatformResult] = []
    error_lines: list[str] = []
    total_new = 0

    pairs = await asyncio.gather(*[_run_one(a) for a in PLATFORMS])

    session = SessionLocal()
    try:
        for adapter, outcome in pairs:
            if isinstance(outcome, Exception):
                msg = f"{adapter.name}: {type(outcome).__name__}: {outcome}"
                log.warning(msg)
                error_lines.append(msg)
                results.append(PlatformResult(platform=adapter.name, total_fetched=0, matches=0, new=0, error=str(outcome)))
                continue

            fetched: list[JobPosting] = outcome
            matches = [j for j in fetched if is_leadership_title(j.title)]
            new_count = 0
            for j in matches:
                exists = session.query(Job).filter_by(url=j.url).first()
                if exists:
                    continue
                session.add(Job(
                    title=j.title.strip()[:500],
                    url=j.url.strip()[:1000],
                    platform=adapter.name,
                    date_found=_dt.date.today(),
                ))
                new_count += 1
            session.commit()
            total_new += new_count
            results.append(PlatformResult(
                platform=adapter.name,
                total_fetched=len(fetched),
                matches=len(matches),
                new=new_count,
            ))

        session.add(RunLog(
            started_at=started,
            finished_at=_dt.datetime.utcnow(),
            new_jobs=total_new,
            errors="\n".join(error_lines) if error_lines else None,
        ))
        session.commit()
    finally:
        session.close()

    return results, total_new


def get_jobs_grouped(only_today: bool = False) -> dict[str, list[dict]]:
    """Return jobs grouped by platform, sorted by date_found desc within each group."""
    session = SessionLocal()
    try:
        q = session.query(Job)
        if only_today:
            q = q.filter(Job.date_found == _dt.date.today())
        rows = q.order_by(Job.date_found.desc(), Job.id.desc()).all()
        grouped: dict[str, list[dict]] = {}
        today = _dt.date.today()
        for r in rows:
            grouped.setdefault(r.platform, []).append({
                "title": r.title,
                "url": r.url,
                "date": r.date_found.isoformat(),
                "is_new_today": r.date_found == today,
            })
        return grouped
    finally:
        session.close()


def get_last_run() -> RunLog | None:
    session = SessionLocal()
    try:
        return session.query(RunLog).order_by(RunLog.id.desc()).first()
    finally:
        session.close()
