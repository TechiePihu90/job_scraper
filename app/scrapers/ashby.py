"""Ashby ATS scraper using the public job-board posting API."""

from __future__ import annotations

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


class AshbyScraper(BaseScraper):
    """Scraper for Ashby job boards.

    Public API: GET https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true
    Returns {"jobs": [...]} in a single response — no pagination or detail calls needed.
    Each posting includes `publishedAt` (a real ISO-8601 timestamp), so recency is
    hour-precise.

    Company config
    --------------
    identifier : Ashby job-board name   e.g. "openai"
    """

    ATS_NAME = "ashby"
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    async def scrape(self) -> list[Job]:
        board = self.company.identifier
        url = f"{self.BASE_URL}/{board}?includeCompensation=true"

        try:
            data = await self._get(url)
        except Exception as exc:
            self.logger.error("Ashby API failed for %s: %s", board, exc)
            return []

        if not isinstance(data, dict):
            self.logger.warning("Ashby: unexpected response type %s for %s", type(data), board)
            return []

        raw_jobs: list[dict] = data.get("jobs", [])
        self.logger.info("Ashby: %d jobs listed for %s", len(raw_jobs), board)

        all_jobs: list[Job] = []
        for raw in raw_jobs:
            try:
                job = self._parse_job(raw)
                if job:
                    all_jobs.append(job)
            except Exception as exc:
                self.logger.warning("Ashby: failed to parse job %s: %s", raw.get("id", "?"), exc)

        self.logger.info("Ashby: %d total jobs scraped for %s", len(all_jobs), board)
        return all_jobs

    def _parse_job(self, raw: dict) -> Job | None:
        # Only include postings that are publicly listed.
        if raw.get("isListed") is False:
            return None

        ext_id: str = str(raw.get("id") or "").strip()
        if not ext_id:
            return None

        title: str = (raw.get("title") or "Unknown").strip()
        location: str = (raw.get("location") or "").strip()
        if not location and isinstance(raw.get("address"), dict):
            addr = raw["address"].get("postalAddress") or {}
            parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
            location = ", ".join(p for p in parts if p)

        description = (raw.get("descriptionPlain") or "").strip()
        if not description:
            description = self.normalize_text(_decode_and_convert(raw.get("descriptionHtml") or ""))

        # publishedAt is a real ISO-8601 timestamp (the genuine post time).
        posted_at: str | None = raw.get("publishedAt") or None

        apply_url: str = (raw.get("applyUrl") or raw.get("jobUrl") or "").strip()

        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=description,
            posted_at=posted_at,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
        )
