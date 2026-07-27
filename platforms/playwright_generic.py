"""Generic SPA scraper that renders the page in headless Chromium and
extracts anchors that look like links to individual job postings.

Heuristics for what counts as a job link:
    - href contains one of: /job, /jobs, /career, /vacancy, /vacancies,
      /position, /opening, /opportunit, /role
    - the anchor text is non-empty and not just navigation chrome
      ("home", "log in", etc.)

We don't filter by keyword here — the orchestrator applies the keyword
matcher uniformly across all adapters.
"""
from __future__ import annotations

import asyncio
import os
import re
from urllib.parse import urljoin, urlparse

from .base import JobPosting, PlatformAdapter, PlatformError

JOB_PATH_RE = re.compile(
    r"/(jobs?|careers?|vacanc(?:y|ies|ija)|position|opening|opportunit|role|"
    r"vakansii|vakansiya)(?:/|\b)",
    re.IGNORECASE,
)
NAV_BLOCKLIST = {
    "home", "about", "contact", "press", "news", "blog", "login", "log in",
    "sign in", "sign up", "log out", "privacy", "terms", "cookies", "help",
    "support", "faq", "all vacancies", "see all", "view all", "все вакансии",
    "о компании", "о нас", "контакты", "поиск", "карьера", "careers",
}
MIN_TITLE_LEN = 5
MAX_TITLE_LEN = 200


# Cap concurrent Chromium instances so we don't OOM the host. Created lazily
# on first use so we bind to the running event loop, not module-import time.
# On small containers (e.g. Render free 512 MB) keep this low.
_BROWSER_SEMAPHORE: asyncio.Semaphore | None = None
# Configurable via env so the same image runs on a tiny 512 MB PaaS box
# (MAX_CONCURRENT_BROWSERS=1) or a roomy VM with lots of RAM (e.g. 4).
try:
    MAX_CONCURRENT_BROWSERS = max(1, int(os.environ.get("MAX_CONCURRENT_BROWSERS", "4")))
except ValueError:
    MAX_CONCURRENT_BROWSERS = 4

# Chromium flags required to run reliably inside a low-memory Linux container:
# --no-sandbox            : no user namespaces available in most PaaS sandboxes
# --disable-dev-shm-usage : container /dev/shm is tiny; write shared memory to /tmp
# --disable-gpu / --single-process style flags trim peak RSS.
_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--no-zygote",
]

# Resource types we don't need for link extraction — blocking them cuts memory
# and network dramatically (Green Software: minimize payload + compute).
_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}


def _get_semaphore() -> asyncio.Semaphore:
    global _BROWSER_SEMAPHORE
    if _BROWSER_SEMAPHORE is None:
        _BROWSER_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
    return _BROWSER_SEMAPHORE


class PlaywrightAdapter(PlatformAdapter):
    async def fetch(self) -> list[JobPosting]:
        # Imported lazily so the rest of the app works even before Playwright
        # browsers are installed.
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise PlatformError(f"Playwright not installed: {e}") from e

        async with _get_semaphore():
            return await self._fetch_with_browser(async_playwright)

    async def _fetch_with_browser(self, async_playwright) -> list[JobPosting]:
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
                try:
                    context = await browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"
                        ),
                        locale="en-US",
                    )
                    # Block heavy resources we never parse — big memory/bandwidth win.
                    async def _block(route):
                        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
                            await route.abort()
                        else:
                            await route.continue_()

                    await context.route("**/*", _block)
                    page = await context.new_page()
                    await page.goto(self.public_url, wait_until="domcontentloaded", timeout=45_000)
                    # Give SPAs a moment to render their job list.
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)

                    anchors = await page.evaluate(
                        """
                        () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                            href: a.href,
                            text: (a.innerText || a.textContent || '').trim()
                        }))
                        """
                    )
                finally:
                    await browser.close()
        except PlatformError:
            raise
        except Exception as e:
            raise PlatformError(f"Playwright render failed: {e}") from e

        host = urlparse(self.public_url).netloc.lower()
        out: dict[str, JobPosting] = {}
        for a in anchors:
            href = (a.get("href") or "").strip()
            text = " ".join((a.get("text") or "").split())
            if not href or not text:
                continue
            if not JOB_PATH_RE.search(href):
                continue
            lowered = text.lower()
            if lowered in NAV_BLOCKLIST or len(text) < MIN_TITLE_LEN or len(text) > MAX_TITLE_LEN:
                continue
            # Skip generic "see all" links — typically a path that is the listing
            # root itself (e.g. /careers without a trailing slug).
            path = urlparse(href).path.rstrip("/")
            if path.count("/") <= 1:
                continue
            abs_url = urljoin(self.public_url, href)
            # Stay within the platform's domain — third-party links are noise.
            link_host = urlparse(abs_url).netloc.lower()
            if host and link_host and host.split(".")[-2:] != link_host.split(".")[-2:]:
                # allow ATS subdomains like jobs.lever.co/foo or boards.greenhouse.io/foo
                if not any(p in link_host for p in ("lever.co", "greenhouse.io", "workable.com", "ashbyhq.com", "smartrecruiters.com")):
                    continue
            out.setdefault(abs_url, JobPosting(title=text, url=abs_url, platform=self.name))
        return list(out.values())
