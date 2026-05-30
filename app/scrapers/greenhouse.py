"""Greenhouse ATS scraper using the public boards API."""

from __future__ import annotations

import asyncio
import html as html_module

from app.models import Job
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 5


def _decode_and_convert(raw: str) -> str:
    """
    Fully decode double-encoded HTML then convert to plain text.

    Greenhouse API returns double-encoded HTML:
        &lt;div class=&quot;content-intro&quot;&gt;
    instead of:
        <div class="content-intro">

    Steps:
      1. Unescape up to 3 times until no entities remain
      2. Pass clean HTML to normalize_text() which uses BeautifulSoup
    """
    if not raw:
        return ""

    decoded = raw
    for _ in range(3):
        if not any(e in decoded for e in ("&lt;", "&gt;", "&amp;", "&quot;", "&#")):
            break
        decoded = html_module.unescape(decoded)

    return decoded  # will be passed to normalize_text() by caller


def _extract_location(raw: dict) -> str:
    loc = raw.get("location") or {}
    if isinstance(loc, dict):
        return (loc.get("name") or "").strip()
    return str(loc).strip()


_US_LOCATION_KEYWORDS = {
    "united states", "usa", "u.s.", "u.s.a", " us",
    " al", " ak", " az", " ar", " ca", " co", " ct", " de", " fl", " ga",
    " hi", " id", " il", " in", " ia", " ks", " ky", " la", " me", " md",
    " ma", " mi", " mn", " ms", " mo", " mt", " ne", " nv", " nh", " nj",
    " nm", " ny", " nc", " nd", " oh", " ok", " or", " pa", " ri", " sc",
    " sd", " tn", " tx", " ut", " vt", " va", " wa", " wv", " wi", " wy",
    "new york", "san francisco", "los angeles", "chicago", "seattle",
    "austin", "boston", "denver", "atlanta", "miami", "dallas",
    "remote",
}


def _is_us_location(location: str) -> bool:
    if not location:
        return False
    loc_lower = location.lower()
    return any(keyword in loc_lower for keyword in _US_LOCATION_KEYWORDS)


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job boards.

    Public API endpoints:
      List   GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
      Detail GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{id}

    The detail endpoint is required — list endpoint does NOT return full description.
    Greenhouse returns double-encoded HTML — we unescape it before passing to
    normalize_text() which uses BeautifulSoup for reliable full-content extraction.

    Company config
    --------------
    identifier  : Greenhouse board token  e.g. "robinhood"
    base_url    : (optional) override API base
    extra       :
        us_only : bool  – if True, skip non-US jobs (default: False)
    """

    ATS_NAME = "greenhouse"
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    async def scrape(self) -> list[Job]:
        board_token = self.company.identifier
        base = (self.company.base_url or self.BASE_URL).rstrip("/")
        us_only: bool = bool((self.company.extra or {}).get("us_only", False))

        if us_only:
            self.logger.info("Greenhouse: US-only filter ENABLED for %s", board_token)

        list_url = f"{base}/{board_token}/jobs"
        try:
            data = await self._get(list_url)
        except Exception as exc:
            self.logger.error("Greenhouse list API failed for %s: %s", board_token, exc)
            return []

        if not isinstance(data, dict):
            self.logger.warning("Unexpected Greenhouse response type %s for %s", type(data), board_token)
            return []

        raw_jobs: list[dict] = data.get("jobs", [])
        self.logger.info("Greenhouse: %d jobs listed for %s", len(raw_jobs), board_token)

        if not raw_jobs:
            return []

        if us_only:
            before = len(raw_jobs)
            raw_jobs = [r for r in raw_jobs if _is_us_location(_extract_location(r))]
            self.logger.info(
                "Greenhouse: US filter removed %d non-US jobs, %d remaining for %s",
                before - len(raw_jobs), len(raw_jobs), board_token,
            )

        if not raw_jobs:
            return []

        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        tasks = [self._process_job(raw, base, board_token, sem) for raw in raw_jobs]
        results = await asyncio.gather(*tasks)

        jobs = [j for j in results if j is not None]
        self.logger.info("Greenhouse: %d/%d jobs scraped for %s", len(jobs), len(raw_jobs), board_token)
        return jobs

    async def _process_job(self, raw: dict, base: str, board_token: str, sem: asyncio.Semaphore) -> Job | None:
        ext_id = str(raw.get("id", "")).strip()
        if not ext_id:
            return None

        async with sem:
            detail = await self._fetch_detail(base, board_token, ext_id)

        if detail:
            raw = {**raw, **detail}

        try:
            return self._parse_job(raw, board_token)
        except Exception as exc:
            self.logger.warning("Greenhouse: failed to parse job %s: %s", ext_id, exc)
            return None

    async def _fetch_detail(self, base: str, board_token: str, ext_id: str) -> dict | None:
        detail_url = f"{base}/{board_token}/jobs/{ext_id}"
        try:
            detail = await self._get(detail_url)
            if isinstance(detail, dict):
                return detail
        except Exception as exc:
            self.logger.debug("Greenhouse: detail fetch failed for %s: %s", ext_id, exc)
        return None

    def _parse_job(self, raw: dict, board_token: str) -> Job | None:
        ext_id = str(raw.get("id", "")).strip()
        if not ext_id:
            return None

        title: str = (raw.get("title") or "Unknown").strip()

        location_obj = raw.get("location") or {}
        if isinstance(location_obj, dict):
            location = (location_obj.get("name") or "").strip()
        else:
            location = str(location_obj).strip()

        departments: list[dict] = raw.get("departments") or []
        department = ", ".join(
            d.get("name", "") for d in departments if isinstance(d, dict) and d.get("name")
        )

        offices: list[dict] = raw.get("offices") or []
        office = ", ".join(
            o.get("name", "") for o in offices if isinstance(o, dict) and o.get("name")
        )

        # KEY FIX:
        # 1. _decode_and_convert() fully unescapes double-encoded HTML
        # 2. normalize_text() uses BeautifulSoup — reliable full-content extraction
        raw_content: str = raw.get("content") or ""
        decoded_content = _decode_and_convert(raw_content)
        description = self.normalize_text(decoded_content)

        posted_at: str | None = raw.get("updated_at") or raw.get("created_at")

        apply_url: str = (
            raw.get("absolute_url")
            or f"https://boards.greenhouse.io/{board_token}/jobs/{ext_id}"
        )

        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=description,
            posted_at=posted_at,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
            # department=department,
            # office=office,
        )