"""One-shot scrape entrypoint.

Runs a single `scrape_all()` pass, logs a per-source summary, then exits.
Designed to be the container command for a **Cloud Run Job** (or any cron /
batch runner). Cloud Scheduler triggers the job on a cadence; this process
does the work and terminates, so you only pay for the few minutes it runs.

    python scrape_job.py
"""
from __future__ import annotations

import asyncio
import logging

from scraper import scrape_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("scrape_job")


async def _main() -> int:
    results, total_new = await scrape_all()
    ok = [r for r in results if not r.error]
    failed = [r for r in results if r.error]
    log.info(
        "Scrape complete: %d new jobs; %d/%d sources ok",
        total_new, len(ok), len(results),
    )
    for r in failed:
        log.warning("  FAILED %s: %s", r.platform, r.error)
    # Exit 0 even on partial source failures — a few blocked sites shouldn't
    # fail the whole job. Only a hard crash (unhandled exception) is non-zero.
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
