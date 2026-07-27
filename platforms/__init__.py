"""Platform adapter registry.

Each platform has a name, source URL and an adapter that knows how to fetch
its job postings. The orchestrator iterates over `PLATFORMS` and asks each
adapter to return a list of `JobPosting` items.
"""
from __future__ import annotations

from .base import JobPosting, PlatformAdapter, PlatformError
from .greenhouse_api import GreenhouseAdapter
from .hh_api import HHEmployerAdapter
from .playwright_generic import PlaywrightAdapter
from .revolut_next import RevolutAdapter

PLATFORMS: list[PlatformAdapter] = [
    # --- Greenhouse-hosted boards. Slug is the company token used on boards-api.greenhouse.io. ---
    GreenhouseAdapter(name="Nebius", slug="nebius", public_url="https://nebius.com/careers"),
    GreenhouseAdapter(name="Toloka", slug="toloka", public_url="https://toloka.ai/careers"),
    GreenhouseAdapter(name="N26",    slug="n26",    public_url="https://n26.com/en-eu/careers"),
    GreenhouseAdapter(name="Flo",    slug="flohealth", public_url="https://flo.health/careers-listing"),
    # Miro / Palta / Xsolla / Mercuryo / Semrush — Greenhouse board IDs guess-checked
    # against boards-api and returned 404 (they use a different ATS or a private board).
    # Falling back to the Playwright generic scraper.
    PlaywrightAdapter(name="Miro",     public_url="https://miro.com/careers/"),
    PlaywrightAdapter(name="Palta",    public_url="https://palta.com/careers"),
    PlaywrightAdapter(name="Xsolla",   public_url="https://xsolla.com/careers"),
    PlaywrightAdapter(name="Mercuryo", public_url="https://mercuryo.io/career/"),
    PlaywrightAdapter(name="Semrush",  public_url="https://careers.semrush.com"),

    # --- HH.ru employer JSON API ---
    HHEmployerAdapter(name="HeadHunter / Yandex",  employer_id="44764",   public_url="https://hh.ru/employer/44764"),
    HHEmployerAdapter(name="HeadHunter / Tinkoff", employer_id="1829949", public_url="https://hh.ru/employer/1829949?tab=VACANCIES"),

    # --- Everything else: render with Playwright and extract job-looking anchors. ---
    PlaywrightAdapter(name="inDrive",     public_url="https://careers.indrive.com/vacancies/"),
    # Revolut: dedicated adapter — parses every position from __NEXT_DATA__ on /careers/.
    RevolutAdapter(),
    PlaywrightAdapter(name="Wise",        public_url="https://wise.jobs/jobs"),
    PlaywrightAdapter(name="BancoPlata",  public_url="https://careers.bancoplata.mx/vacancy"),
    PlaywrightAdapter(name="Novatech",    public_url="https://novatech.ru/about/"),
    PlaywrightAdapter(name="Novatech KZ", public_url="https://novatech-corp.kz"),
    PlaywrightAdapter(name="AppFollow",   public_url="https://appfollow.io/team"),
    PlaywrightAdapter(name="JetBrains",   public_url="https://www.jetbrains.com/careers/jobs/"),
    PlaywrightAdapter(name="Avito",       public_url="https://career.avito.com/vacancies/"),
    PlaywrightAdapter(name="SberTech",    public_url="https://sbertech.ru/career"),
    PlaywrightAdapter(name="Sber Rabota", public_url="https://rabota.sber.ru/search/"),
    PlaywrightAdapter(name="Ozon Tech",   public_url="https://ozon.tech/"),
    PlaywrightAdapter(name="Aviasales",   public_url="https://www.aviasales.ru/about/vacancies"),
    PlaywrightAdapter(name="T-Bank",      public_url="https://job.tinkoff.ru"),
]

__all__ = [
    "JobPosting",
    "PlatformAdapter",
    "PlatformError",
    "PLATFORMS",
]
