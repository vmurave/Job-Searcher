"""Revolut careers adapter.

Revolut's careers site is built on Next.js. The main `/careers/` page server-
renders the complete list of open positions into a `<script id="__NEXT_DATA__">`
JSON blob — `props.pageProps.positions` is an array of ~600+ items, one per
job, with title, team, locations, and id.

Scrolling/team-page traversal isn't needed: one fetch gets every vacancy.
However, the site is behind Cloudflare and returns 403 to plain HTTP clients,
so we render with headless Chromium via Playwright.
"""
from __future__ import annotations

import asyncio
import json
import re

from .base import JobPosting, PlatformAdapter, PlatformError
from .playwright_generic import _get_semaphore  # reuse Chromium concurrency cap

CAREERS_URL = "https://www.revolut.com/careers/"
POSITION_URL_TEMPLATE = "https://www.revolut.com/careers/position/{slug}-{id}/"
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


class RevolutAdapter(PlatformAdapter):
    def __init__(self, name: str = "Revolut", public_url: str = CAREERS_URL) -> None:
        super().__init__(name=name, public_url=public_url)

    async def fetch(self) -> list[JobPosting]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise PlatformError(f"Playwright not installed: {e}") from e

        async with _get_semaphore():
            html = await self._fetch_html(async_playwright)

        m = _NEXT_DATA_RE.search(html)
        if not m:
            raise PlatformError("Revolut: __NEXT_DATA__ script not found in HTML")
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            raise PlatformError(f"Revolut: __NEXT_DATA__ is not valid JSON: {e}") from e

        positions = (
            data.get("props", {}).get("pageProps", {}).get("positions")
        )
        if not isinstance(positions, list):
            raise PlatformError("Revolut: props.pageProps.positions missing or not a list")

        jobs: dict[str, JobPosting] = {}
        for p in positions:
            title = (p.get("text") or "").strip()
            pid = (p.get("id") or "").strip()
            if not title or not pid:
                continue
            url = POSITION_URL_TEMPLATE.format(slug=_slugify(title), id=pid)
            jobs.setdefault(url, JobPosting(title=title, url=url, platform=self.name))
        return list(jobs.values())

    async def _fetch_html(self, async_playwright) -> str:
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"
                        ),
                        locale="en-US",
                    )
                    page = await context.new_page()
                    await page.goto(self.public_url, wait_until="domcontentloaded", timeout=60_000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:
                        pass
                    await asyncio.sleep(1)
                    return await page.content()
                finally:
                    await browser.close()
        except PlatformError:
            raise
        except Exception as e:
            raise PlatformError(f"Revolut render failed: {e}") from e
