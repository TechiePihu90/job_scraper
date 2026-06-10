"""Workday ATS scraper using the internal CXS search + detail API."""

from __future__ import annotations

import asyncio
import html as html_module
import re

from app.models import Job
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 5


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


def _safe_get(d: dict, *keys: str) -> object:
    current: object = d
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


class WorkdayScraper(BaseScraper):
    """Scraper for Workday career sites.

    Uses Workday's internal CXS API:
      Search  POST {host}/wday/cxs/{tenant}/{site_path}/jobs
      Detail  GET  {host}/wday/cxs/{tenant}/{site_path}/jobs/{ext_id}

    Uses normalize_text() (BeautifulSoup) after unescape for full reliable extraction.

    Company config
    --------------
    identifier : "tenant/site_path"   e.g. "apple/Apple"
    base_url   : Workday host          e.g. "https://apple.wd5.myworkdayjobs.com"
    extra      : (optional)
        location_facet : list[str]  -- Workday location IDs to filter by
        locale         : str        -- override URL locale (default "en-US")
    """

    ATS_NAME = "workday"
    PAGE_SIZE = 20

    async def scrape(self) -> list[Job]:
        parts = self.company.identifier.split("/", 1)
        if len(parts) != 2:
            self.logger.error("Invalid Workday identifier '%s'. Expected 'tenant/site_path'.", self.company.identifier)
            return []

        tenant, site_path = parts
        host = (self.company.base_url or "").rstrip("/")

        if not host:
            self.logger.error("Workday requires base_url (e.g. 'https://company.wd5.myworkdayjobs.com')")
            return []

        locale = (self.company.extra or {}).get("locale", "en-US")
        search_url = f"{host}/wday/cxs/{tenant}/{site_path}/jobs"

        all_jobs: list[Job] = []
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        offset = 0
        total: int | None = None
        page = 0

        while True:
            page += 1
            payload: dict = {
                "appliedFacets": {},
                "limit": self.PAGE_SIZE,
                "offset": offset,
                "searchText": "",
            }

            location_facet = (self.company.extra or {}).get("location_facet")
            if location_facet:
                payload["appliedFacets"]["locations"] = location_facet

            self.logger.debug("Workday page %d (offset=%d)", page, offset)

            try:
                data = await self._post(search_url, json_data=payload)
            except Exception as exc:
                self.logger.error("Workday search API error on page %d: %s", page, exc)
                break

            if not isinstance(data, dict):
                self.logger.warning("Unexpected Workday response type %s on page %d", type(data), page)
                break

            if total is None:
                total = int(data.get("total", 0))
                self.logger.info("Workday: %d total jobs for %s", total, self.company.name)
                if total == 0:
                    break

            job_postings: list[dict] = data.get("jobPostings", [])
            if not job_postings:
                self.logger.debug("Workday: empty jobPostings at offset %d — stopping", offset)
                break

            tasks = [self._process_job(raw, host, tenant, site_path, locale, sem) for raw in job_postings]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            fetched = 0
            for j in results:
                if j is not None:
                    all_jobs.append(j)
                    fetched += 1

            self.logger.debug("Workday page %d: %d/%d jobs parsed", page, fetched, len(job_postings))

            offset += len(job_postings)
            if total is not None and offset >= total:
                break

        self.logger.info("Workday: finished — %d jobs scraped for %s", len(all_jobs), self.company.name)
        return all_jobs

    async def _process_job(self, raw, host, tenant, site_path, locale, sem) -> Job | None:
        try:
            job = self._parse_job(raw, host, site_path, locale)
            if job is None:
                return None
            async with sem:
                await self._enrich_description(job, raw, host, tenant, site_path)
            return job
        except Exception as exc:
            self.logger.warning("Workday: failed to process job (title=%s): %s", raw.get("title", "?"), exc)
            return None

    async def _enrich_description(self, job: Job, raw: dict, host: str, tenant: str, site_path: str) -> None:
        external_path: str = raw.get("externalPath", "")
        if not external_path:
            return

        ext_id = external_path.rstrip("/").split("/")[-1]
        if not ext_id:
            return

        # Workday detail endpoint is the singular "/job" path with the FULL
        # externalPath (e.g. ".../JCI/job/Chicago-.../Title_WD123"). Using the
        # plural "/jobs/{last-segment}" search path returns HTTP 422.
        path = external_path if external_path.startswith("/") else "/" + external_path
        detail_url = f"{host}/wday/cxs/{tenant}/{site_path}{path}"

        try:
            detail: object = await self._get(detail_url)
        except Exception as exc:
            self.logger.debug("Workday detail fetch failed for %s: %s", ext_id, exc)
            return

        if not isinstance(detail, dict):
            return

        desc = self._extract_description(detail)
        if desc:
            job.description = desc

        posted = self._extract_posted_date(detail)
        if posted:
            job.posted_at = posted

    @staticmethod
    def _extract_posted_date(detail: dict) -> str | None:
        """Extract the real ISO posting date from a Workday detail response.

        The search/list API only returns a relative string ("Posted Today"),
        which cannot be parsed into a date. The detail API exposes the real
        date as jobPostingInfo.startDate (e.g. "2026-06-09").
        """
        for container_key in ("jobPostingInfo", "jobPosting"):
            info = detail.get(container_key)
            if isinstance(info, dict):
                for key in ("startDate", "postedOnDate", "datePosted"):
                    val = info.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        return None

    def _extract_description(self, detail: dict) -> str:
        """
        Pull the richest job description from the detail API response.

        KEY FIX:
        1. _decode_and_convert() fully unescapes double-encoded HTML
        2. normalize_text() uses BeautifulSoup — full reliable extraction
           (no mid-content truncation unlike custom HTMLParser)

        Workday description possible locations:
          detail["jobPostingInfo"]["jobDescription"]  -- most common
          detail["jobPosting"]["jobDescription"]
          detail["jobDescription"]
          detail["description"]
        """
        candidates: list[str] = []

        sources: list[tuple[dict, str]] = []

        info = detail.get("jobPostingInfo")
        if isinstance(info, dict):
            sources.append((info, "jobDescription"))
            sources.append((info, "description"))
            sources.append((info, "jobSummary"))
            sources.append((info, "additionalJobDescription"))

        posting = detail.get("jobPosting")
        if isinstance(posting, dict):
            sources.append((posting, "jobDescription"))
            sources.append((posting, "description"))

        sources.append((detail, "jobDescription"))
        sources.append((detail, "description"))
        sources.append((detail, "content"))
        sources.append((detail, "descriptionPlain"))

        for container, key in sources:
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

        if not candidates:
            return ""

        # Unescape all candidates first, then pick longest real content
        decoded_candidates = [_decode_and_convert(c) for c in candidates]
        best = max(decoded_candidates, key=len)

        # normalize_text() uses BeautifulSoup — handles full HTML reliably
        return self.normalize_text(best)

    def _parse_job(self, raw: dict, host: str, site_path: str, locale: str) -> Job | None:
        external_path: str = raw.get("externalPath", "")
        ext_id = external_path.rstrip("/").split("/")[-1] if external_path else ""

        if not ext_id:
            bullet_fields: list = raw.get("bulletFields") or []
            ext_id = bullet_fields[0] if bullet_fields else ""

        if not ext_id:
            self.logger.debug("Workday: skipping job with no ID — raw keys: %s", list(raw))
            return None

        title: str = html_module.unescape((raw.get("title") or "Unknown").strip())

        location: str = (raw.get("locationsText") or "").strip()
        if not location:
            primary = raw.get("primaryLocation") or {}
            if isinstance(primary, dict):
                city = primary.get("city") or ""
                state = primary.get("stateProvinceAbbreviation") or ""
                country = primary.get("countryAlpha2Code") or ""
                parts = [p for p in [city, state, country] if p]
                location = ", ".join(parts)
        if not location:
            bullet_fields = raw.get("bulletFields") or []
            if len(bullet_fields) > 1:
                location = str(bullet_fields[1]).strip()

        remote_type: str = (raw.get("remoteType") or "").strip()

        work_type: str = ""
        work_type_raw = raw.get("jobType") or raw.get("workType") or raw.get("employmentType") or ""
        if isinstance(work_type_raw, str):
            work_type = work_type_raw.strip()
        elif isinstance(work_type_raw, dict):
            work_type = (work_type_raw.get("descriptor") or "").strip()

        # The Workday search/list API only exposes a relative string here
        # (e.g. "Posted Today"), which is not a parseable date. The real
        # posting date is read from the detail API in _enrich_description().
        posted_at: str | None = None

        closes_at: str | None = (
            raw.get("closingDate")
            or raw.get("endDate")
            or _safe_get(raw, "jobPostingInfo", "endDate")
            or _safe_get(raw, "jobPostingInfo", "closingDate")
        )

        department: str = ""
        dept_raw = raw.get("organizationHierarchy") or raw.get("department") or {}
        if isinstance(dept_raw, dict):
            department = (dept_raw.get("descriptor") or "").strip()
        elif isinstance(dept_raw, str):
            department = dept_raw.strip()

        apply_url = self._build_apply_url(host, site_path, locale, external_path)

        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description="",   # filled by _enrich_description
            posted_at=posted_at,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
            # closes_at=closes_at,
            # department=department,
            # work_type=work_type,
            # remote_type=remote_type,
        )

    def _build_apply_url(self, host: str, site_path: str, locale: str, external_path: str) -> str:
        if not external_path:
            return host
        if not external_path.startswith("/"):
            external_path = "/" + external_path
        if re.match(r"^/[a-z]{2}-[A-Z]{2}/", external_path):
            return f"{host}{external_path}"
        clean_site = site_path.strip("/")
        if f"/{clean_site}/" in external_path or external_path.startswith(f"/{clean_site}/"):
            return f"{host}{external_path}"
        return f"{host}/{locale}/{clean_site}{external_path}"