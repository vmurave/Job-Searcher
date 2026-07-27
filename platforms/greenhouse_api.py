"""Greenhouse public board API adapter.

Greenhouse exposes a public read-only board at:
    https://boards-api.greenhouse.io/v1/boards/{slug}/jobs

The slug is the company token. If a company doesn't actually host on Greenhouse
the request 404s and we raise PlatformError so the orchestrator can mark it.
"""
from __future__ import annotations

import httpx

from .base import JobPosting, PlatformAdapter, PlatformError

API_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseAdapter(PlatformAdapter):
    def __init__(self, name: str, slug: str, public_url: str) -> None:
        super().__init__(name=name, public_url=public_url)
        self.slug = slug

    async def fetch(self) -> list[JobPosting]:
        url = API_TEMPLATE.format(slug=self.slug)
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "leadership-jobs-bot/1.0"})
        except httpx.HTTPError as e:
            raise PlatformError(f"Greenhouse request failed: {e}") from e

        if resp.status_code == 404:
            raise PlatformError(f"Greenhouse board '{self.slug}' not found")
        if resp.status_code >= 400:
            raise PlatformError(f"Greenhouse returned HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except ValueError as e:
            raise PlatformError(f"Greenhouse returned non-JSON: {e}") from e

        jobs: list[JobPosting] = []
        for item in payload.get("jobs", []):
            title = (item.get("title") or "").strip()
            url = (item.get("absolute_url") or "").strip()
            if title and url:
                jobs.append(JobPosting(title=title, url=url, platform=self.name))
        return jobs
