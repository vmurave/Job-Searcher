"""HH.ru public vacancies API adapter.

Docs: https://api.hh.ru/openapi/redoc#tag/Poisk-vakansij
Endpoint: GET https://api.hh.ru/vacancies?employer_id={id}&per_page=100&page=N

The API caps each page at 100 results and returns at most 2000 in total.
"""
from __future__ import annotations

import asyncio

import httpx

from .base import JobPosting, PlatformAdapter, PlatformError

API = "https://api.hh.ru/vacancies"


class HHEmployerAdapter(PlatformAdapter):
    def __init__(self, name: str, employer_id: str, public_url: str) -> None:
        super().__init__(name=name, public_url=public_url)
        self.employer_id = employer_id

    async def fetch(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        async with httpx.AsyncClient(timeout=20) as client:
            page = 0
            while True:
                params = {"employer_id": self.employer_id, "per_page": 100, "page": page}
                # HH.ru API requires a UA in "AppName/Version (contact)" format and
                # also accepts the legacy HH-User-Agent header. Send both — some
                # edge proxies validate one and not the other.
                headers = {
                    "User-Agent": "LeadershipJobsDigest/1.0 (mailto:viacheslav.muravets@accenture.com)",
                    "HH-User-Agent": "LeadershipJobsDigest/1.0 (mailto:viacheslav.muravets@accenture.com)",
                    "Accept": "application/json",
                }
                try:
                    resp = await client.get(API, params=params, headers=headers)
                except httpx.HTTPError as e:
                    raise PlatformError(f"HH.ru request failed: {e}") from e
                if resp.status_code >= 400:
                    raise PlatformError(f"HH.ru HTTP {resp.status_code}")
                data = resp.json()
                for item in data.get("items", []):
                    title = (item.get("name") or "").strip()
                    url = (item.get("alternate_url") or "").strip()
                    if title and url:
                        jobs.append(JobPosting(title=title, url=url, platform=self.name))
                if page + 1 >= data.get("pages", 0):
                    break
                page += 1
                await asyncio.sleep(0.2)  # be polite
        return jobs
