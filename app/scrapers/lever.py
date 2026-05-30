"""Lever ATS scraper using the public postings API."""

from __future__ import annotations

import datetime
import html as html_module

from app.models import Job
from app.scrapers.base import BaseScraper


def _decode_and_convert(raw: str) -> str:
    """Fully unescape double-encoded HTML for normalize_text()."""
    if not raw:
        return ""
    decoded = raw
    for _ in range(3):
        if not any(e in decoded for e in ("&lt;", "&gt;", "&amp;", "&quot;", "&#")):
            break
        decoded = html_module.unescape(decoded)
    return decoded


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
    return any(kw in loc_lower for kw in _US_LOCATION_KEYWORDS)


class LeverScraper(BaseScraper):
    """Scraper for Lever job boards.

    Public API: https://api.lever.co/v0/postings/{company}
    Supports cursor-based pagination via ?offset=<id>.

    Lever returns FULL description in the list response itself — no detail call needed.
    Description is split across three HTML fields:
      • description  – intro / overview
      • lists[]      – structured sections (Responsibilities, Requirements, etc.)
      • additional   – closing section (perks, benefits, etc.)

    Uses normalize_text() (BeautifulSoup) after unescape for full reliable extraction.

    Company config
    --------------
    identifier : Lever company slug   e.g. "netflix"
    base_url   : (optional) override API base
    extra      :
        us_only : bool  – if True, skip non-US jobs (default: False)
    """

    ATS_NAME = "lever"
    BASE_URL = "https://api.lever.co/v0/postings"

    async def scrape(self) -> list[Job]:
        company_slug = self.company.identifier
        base = (self.company.base_url or self.BASE_URL).rstrip("/")
        us_only: bool = bool((self.company.extra or {}).get("us_only", False))

        if us_only:
            self.logger.info("Lever: US-only filter ENABLED for %s", company_slug)

        all_jobs: list[Job] = []
        offset: str | None = None
        page = 0

        while True:
            page += 1
            url = f"{base}/{company_slug}?mode=json&limit=100"
            if offset:
                url += f"&offset={offset}"

            self.logger.debug("Lever page %d (offset=%s)", page, offset)

            try:
                data = await self._get(url)
            except Exception as exc:
                self.logger.error("Lever API failed for %s: %s", company_slug, exc)
                break

            if not isinstance(data, list):
                self.logger.warning("Lever: unexpected response type %s for %s", type(data), company_slug)
                break

            if not data:
                break

            for raw in data:
                try:
                    job = self._parse_job(raw)
                    if not job:
                        continue
                    if us_only and not _is_us_location(job.location or ""):
                        continue
                    all_jobs.append(job)
                except Exception as exc:
                    self.logger.warning("Lever: failed to parse job %s: %s", raw.get("id", "?"), exc)

            if len(data) < 100:
                break

            last_id = data[-1].get("id")
            if not last_id or last_id == offset:
                break
            offset = last_id

        self.logger.info("Lever: %d total jobs scraped for %s", len(all_jobs), company_slug)
        return all_jobs

    def _parse_job(self, raw: dict) -> Job | None:
        ext_id: str = (raw.get("id") or "").strip()
        if not ext_id:
            return None

        title: str = (raw.get("text") or "Unknown").strip()

        categories: dict = raw.get("categories") or {}
        location: str = (categories.get("location") or "").strip()
        if not location:
            location = (raw.get("workplaceType") or "").strip()

        team: str = (categories.get("team") or "").strip()
        commitment: str = (categories.get("commitment") or "").strip()
        department: str = (categories.get("department") or "").strip()

        # KEY FIX:
        # 1. _decode_and_convert() unescapes double-encoded HTML
        # 2. normalize_text() uses BeautifulSoup — full reliable extraction
        parts: list[str] = []

        desc_text = self.normalize_text(_decode_and_convert(raw.get("description") or ""))
        if desc_text:
            parts.append(desc_text)

        for lst in raw.get("lists") or []:
            heading = html_module.unescape((lst.get("text") or "").strip())
            content_text = self.normalize_text(_decode_and_convert(lst.get("content") or ""))
            if heading:
                parts.append(heading)
            if content_text:
                parts.append(content_text)

        additional_text = self.normalize_text(_decode_and_convert(raw.get("additional") or ""))
        if additional_text:
            parts.append(additional_text)

        description = "\n\n".join(filter(None, parts))

        posted_at: str | None = None
        created_at = raw.get("createdAt")
        if created_at:
            try:
                posted_at = datetime.datetime.fromtimestamp(
                    int(created_at) / 1000, tz=datetime.timezone.utc
                ).isoformat()
            except Exception:
                posted_at = str(created_at)

        apply_url: str = (raw.get("hostedUrl") or raw.get("applyUrl") or "").strip()

        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=description,
            posted_at=posted_at,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
            # team=team,
            # department=department,
            # commitment=commitment,
        )