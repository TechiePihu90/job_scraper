"""USAJOBS scraper using the official Search API."""

from __future__ import annotations

import re
import html
from app.models import Job
from app.scrapers.base import BaseScraper
from app.config import settings


class USAJobsScraper(BaseScraper):
    """Scraper for USAJOBS.gov using the Search API.
    
    Documentation: https://developer.usajobs.gov/API-Reference/GET-api-Search
    Requires JOBSCRAPER_USAJOBS_API_KEY and JOBSCRAPER_USAJOBS_USER_AGENT.
    """

    ATS_NAME = "usajobs"
    BASE_URL = "https://data.usajobs.gov/api/Search"

    # IT-related keyword searches to pull more relevant jobs
    IT_KEYWORDS = [
        "software engineer",
        "data engineer",
        "cybersecurity",
        "cloud",
        "IT specialist",
        "systems administrator",
        "network engineer",
        "DevOps",
        "machine learning",
        "information technology",
    ]

    async def scrape(self) -> list[Job]:
        """Fetch IT jobs from USAJOBS across multiple keyword searches."""
        api_key = settings.usajobs_api_key
        user_agent = settings.usajobs_user_agent or "JobScraper/1.0"
        
        if not api_key:
            self.logger.warning(
                "USAJOBS API key not configured. To enable USAJOBS scraping, set JOBSCRAPER_USAJOBS_API_KEY in .env"
            )
            return []

        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": user_agent,
            "Authorization-Key": api_key,
        }

        seen_ids: set[str] = set()
        all_jobs: list[Job] = []

        for keyword in self.IT_KEYWORDS:
            page_size = 500
            for page in range(1, 3):  # up to 2 pages per keyword
                params = {
                    "Keyword": keyword,
                    "ResultsPerPage": page_size,
                    "Page": page,
                    "LocationName": "United States",
                }
                try:
                    data = await self._get(self.BASE_URL, headers=headers, params=params)
                except Exception as exc:
                    self.logger.error("USAJOBS API failed (keyword=%s, page=%d): %s", keyword, page, exc)
                    break

                if not isinstance(data, dict):
                    break

                search_results = data.get("SearchResult", {}).get("SearchResultItems", [])
                if not search_results:
                    break

                for item in search_results:
                    raw = item.get("MatchedObjectDescriptor", {})
                    ext_id = raw.get("PositionID")
                    if ext_id and ext_id not in seen_ids:
                        seen_ids.add(ext_id)
                        job = self._parse_job(raw)
                        if job:
                            all_jobs.append(job)

                if len(search_results) < page_size:
                    break

        self.logger.info("USAJOBS fetched %d unique jobs across all keyword searches", len(all_jobs))
        return all_jobs

    def _parse_job(self, raw: dict) -> Job | None:
        """Parse a USAJOBS item."""
        ext_id = raw.get("PositionID")
        if not ext_id:
            return None

        # Locations can be multiple
        locations = raw.get("PositionLocation", [])
        loc_str = ", ".join([loc.get("LocationName", "") for loc in locations[:2]])

        # Description - prefer JobSummary, fall back to QualificationSummary
        summary = raw.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
        if not summary:
            summary = raw.get("QualificationSummary", "")

        description = self.normalize_text(summary)

        # Build the correct human-facing apply URL.
        # ApplyURI contains the actual "Apply" button URLs (could be USA Staffing etc.)
        # PositionURI is the USAJOBS data-API URL — NOT clickable for applicants.
        # The canonical public job page is: https://www.usajobs.gov/job/{PositionID}
        apply_uris = raw.get("UserArea", {}).get("Details", {}).get("ApplyURI", [])
        if apply_uris and isinstance(apply_uris, list) and apply_uris[0]:
            apply_url = apply_uris[0]
        else:
            # Fallback: direct USAJOBS public job page
            apply_url = f"https://www.usajobs.gov/job/{ext_id}"

        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, "USAJOBS", ext_id),
            title=raw.get("PositionTitle", "Unknown"),
            company=raw.get("OrganizationName", "US Government"),
            location=loc_str,
            description=description,
            posted_at=raw.get("PublicationStartDate"),
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
        )
