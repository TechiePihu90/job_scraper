"""Dayforce ATS scraper for Ceridian Dayforce career portals."""

from __future__ import annotations

import asyncio
import html
import re
import time

from app.models import Job
from app.scrapers.base import BaseScraper


class DayforceScraper(BaseScraper):
    """Scraper for Dayforce career sites (Ceridian HCM platform).

    Uses the public Dayforce API endpoint:
        https://jobs.dayforcehcm.com/api/geo/{client_namespace}/jobposting/search

    The company identifier should be the client_namespace (e.g., 'baltimoreravens').
    Filters jobs to USA locations only.
    """

    ATS_NAME = "dayforce"
    PAGE_SIZE = 25
    CULTURE_CODE = "en-US"
    JOB_BOARD_CODE = "CANDIDATEPORTAL"

    async def scrape(self) -> list[Job]:
        """Fetch all USA jobs from a Dayforce job board using the public API."""
        client_namespace = self.company.identifier
        all_jobs: list[Job] = []
        offset = 0

        while True:
            self.logger.debug("Dayforce offset %d for %s", offset, self.company.name)

            # Fetch a page of jobs
            jobs_page = await self._fetch_page(client_namespace, offset)
            
            if not jobs_page:
                break

            # Parse and filter for USA jobs only
            parsed_jobs = []
            for raw_job in jobs_page:
                job = self._parse_job(raw_job)
                if job:
                    parsed_jobs.append(job)

            all_jobs.extend(parsed_jobs)
            self.logger.debug("Got %d jobs in this batch, total: %d", len(parsed_jobs), len(all_jobs))

            # Check if we got fewer than page size (indicates last page)
            if len(jobs_page) < self.PAGE_SIZE:
                break

            offset += self.PAGE_SIZE
            await asyncio.sleep(0.5)  # Be respectful to the API

        self.logger.info("Dayforce fetched %d USA jobs for %s", len(all_jobs), self.company.name)
        return all_jobs

    async def _fetch_page(self, client_namespace: str, offset: int) -> list[dict]:
        """Fetch a single page of jobs from Dayforce API."""
        try:
            url = f"https://jobs.dayforcehcm.com/api/geo/{client_namespace}/jobposting/search"
            
            payload = {
                "clientNamespace": client_namespace,
                "jobBoardCode": self.JOB_BOARD_CODE,
                "cultureCode": self.CULTURE_CODE,
                "distanceUnit": 0,
                "paginationStart": offset
            }
            
            headers = {"Content-Type": "application/json"}
            
            self.logger.debug("Fetching from Dayforce API: %s", url)
            data = await self._post(url, json=payload, headers=headers)
            
            if not isinstance(data, dict):
                self.logger.debug("Dayforce API returned non-dict response: %s", type(data))
                return []
            
            jobs = data.get("jobPostings", [])
            if not isinstance(jobs, list):
                self.logger.debug("No jobPostings in response. Keys: %s", list(data.keys()))
                return []
            
            self.logger.debug("Dayforce API returned %d jobs", len(jobs))
            return jobs
                
        except Exception as e:
            self.logger.debug("Failed to fetch Dayforce page at offset %d: %s", offset, str(e)[:100])
            return []

    def _parse_job(self, raw: dict) -> Job | None:
        """Parse a single Dayforce job object into a normalized Job.
        
        Filters for USA jobs only.
        """
        try:
            # Extract job ID
            job_id = raw.get("jobPostingId") or raw.get("jobId") or raw.get("id")
            if not job_id:
                return None

            # Extract primary location (first location if multiple)
            locations = raw.get("postingLocations", [])
            if not locations:
                self.logger.debug("Job %s has no locations", job_id)
                return None
            
            primary_location = locations[0] if isinstance(locations, list) else {}
            
            # Filter for USA jobs only
            country_code = primary_location.get("isoCountryCode", "")
            if country_code.upper() != "US":
                self.logger.debug("Skipping non-USA job %s (country: %s)", job_id, country_code)
                return None
            
            # Extract location details
            city = primary_location.get("cityName", "")
            state = primary_location.get("stateCode", "")
            location = primary_location.get("formattedAddress", "")
            
            # If no formatted address, build from city/state
            if not location and (city or state):
                location = f"{city}, {state}".strip(", ")
            
            title = raw.get("jobTitle", "Unknown")
            
            # Build apply URL from API identifiers
            culture_code = self.CULTURE_CODE
            client_namespace = self.company.identifier
            job_board_code = self.JOB_BOARD_CODE
            apply_url = f"https://jobs.dayforcehcm.com/{culture_code}/{client_namespace}/{job_board_code}/jobs/{job_id}"
            
            # Extract and clean description (HTML)
            description = raw.get("jobDescription", "")
            if description:
                description = self.normalize_text(description)
            
            # Extract posted date (UTC timestamp)
            posted_at = raw.get("postingStartTimestampUTC") or raw.get("postedDate")
            
            # Extract additional fields
            department = raw.get("department", "")
            
            return Job(
                job_id=self.generate_job_id(self.ATS_NAME, self.company.name, str(job_id)),
                title=title,
                company=self.company.name,
                location=location,
                department=department,
                description=description,
                posted_at=posted_at,
                apply_url=apply_url,
                source_ats=self.ATS_NAME,
            )
        except Exception as e:
            self.logger.warning("Failed to parse Dayforce job %s: %s", raw.get("jobPostingId"), e)
            return None
