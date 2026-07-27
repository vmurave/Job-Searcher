"""Standalone CLI entry: run a scrape once and print a summary.

Useful for testing locally or wiring up an external cron.
Scheduling for the running app lives in `main.py` (APScheduler in FastAPI lifespan).

    py -3 scheduler.py
"""
from __future__ import annotations

import asyncio
import logging

from scraper import scrape_all


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
    results, total_new = asyncio.run(scrape_all())
    print(f"\nTotal new jobs: {total_new}")
    for r in results:
        status = f"ERR: {r.error}" if r.error else f"fetched={r.total_fetched} matches={r.matches} new={r.new}"
        print(f"  {r.platform:30s} {status}")


if __name__ == "__main__":
    main()
