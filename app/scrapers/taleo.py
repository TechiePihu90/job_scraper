"""Oracle Taleo ATS scraper — scaffold implementation."""

from __future__ import annotations

from app.models import Job
from app.scrapers.base import BaseScraper


class TaleoScraper(BaseScraper):
    """Scraper for Oracle Taleo career sites.

    Uses the Taleo REST API:
        POST {base_url}/careersection/rest/jobboard/searchjobs?portal={id}

    Identifier: Portal ID (e.g., "10161" for some sites)
    base_url: The Taleo host (e.g., "https://starbucks.taleo.net")
    """

    ATS_NAME = "taleo"

    async def scrape(self) -> list[Job]:
        """Fetch all jobs from Taleo using the REST API."""
        base = self.company.base_url
        if not base:
            self.logger.error("Taleo requires base_url")
            return []

        # Identifier is often the portal ID; fallback to '1' if not provided
        portal_id = self.company.identifier or "1"
        search_url = f"{base.rstrip('/')}/careersection/rest/jobboard/searchjobs?portal={portal_id}"
        
        payload = {
            "multilineEnabled": False,
            "sortingSelection": {"fieldId": "post_date", "sortOrder": 1},
            "fieldData": {"fields": {"keyword": "", "location": -1, "category": -1}, "valid": True},
            "filterSelection": {"fieldData": {"fields": {}, "valid": True}, "filterEntries": []},
            "pageIndex": 1,
        }

        all_jobs: list[Job] = []
        page = 1

        while True:
            payload["pageIndex"] = page
            self.logger.debug("Taleo page %d: %s", page, search_url)

            try:
                # Taleo often needs specific headers
                headers = {
                    "Content-Type": "application/json",
                    "tz": "GMT+05:30",
                    "Referer": f"{base}/careersection/2/jobsearch.ftl",
                }
                data = await self._post(search_url, json_data=payload, headers=headers)
            except Exception as exc:
                self.logger.error("Taleo search failed: %s", exc)
                break

            if not isinstance(data, dict):
                break

            # Taleo response has 'requisitionList'
            job_list = data.get("requisitionList", [])
            if not job_list:
                break

            for raw in job_list:
                try:
                    job = self._parse_job(raw, base)
                    if job:
                        all_jobs.append(job)
                except Exception as exc:
                    self.logger.warning("Failed to parse Taleo job: %s", exc)

            # Check if we have more pages
            total = data.get("totalCount", 0)
            if len(all_jobs) >= total:
                break

            page += 1

        return all_jobs

    def _parse_job(self, raw: dict, base: str) -> Job | None:
        """Parse a single Taleo requisition."""
        ext_id = str(raw.get("contestNo") or raw.get("jobId") or "")
        if not ext_id:
            return None

        title = raw.get("column", [{}])[0].get("value") or "Unknown"
        location = raw.get("column", [{}, {}])[1].get("value") or ""
        
        # Build apply URL
        # Taleo URLs are typically: {base}/careersection/2/jobdetail.ftl?job={jobId}
        job_id_num = raw.get("jobId")
        apply_url = f"{base.rstrip('/')}/careersection/2/jobdetail.ftl?job={job_id_num}"
        
        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=title, # Full JD requires a separate call
            posted_at=None,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
        )
