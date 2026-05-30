"""BambooHR ATS scraper using public JSON API."""

from __future__ import annotations

import re
import asyncio
import aiohttp
from app.models import Job
from app.scrapers.base import BaseScraper

# US state abbreviations for location filtering
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}


class BambooHRScraper(BaseScraper):
    """Scraper for BambooHR using public API.

    BambooHR exposes a public API at:
        https://{company}.bamboohr.com/careers/list
        https://{company}.bamboohr.com/careers/{job_id}/detail

    Identifier should be the BambooHR company subdomain.
    """

    ATS_NAME = "bamboohr"

    async def scrape(self) -> list[Job]:
        """Fetch all USA jobs from BambooHR using public API."""
        subdomain = self.company.identifier
        base_url = f"https://{subdomain}.bamboohr.com"

        try:
            # Validate company exists
            company_info = await self._fetch_company_info(base_url)
            if not company_info:
                self.logger.warning("BambooHR company '%s' not found or invalid", subdomain)
                return []

            company_name = company_info.get("name", subdomain)
            self.logger.info("Found BambooHR company: %s", company_name)

            # Fetch all job listings
            jobs_data = await self._fetch_job_listings(base_url)
            if not jobs_data:
                self.logger.info("No jobs found for BambooHR company: %s", subdomain)
                return []

            self.logger.info("Found %d job listings for %s", len(jobs_data), subdomain)

            # Fetch details for each job and filter for USA
            jobs = []
            for i, job in enumerate(jobs_data):
                try:
                    job_id = job.get("id")
                    if not job_id:
                        continue

                    details = await self._fetch_job_details(base_url, job_id)
                    if not details:
                        self.logger.debug("Failed to fetch details for job %s", job_id)
                        continue

                    # Check if job is in USA
                    location_info = job.get("atsLocation", {})
                    state = location_info.get("state", "")
                    country = location_info.get("country", "US")

                    # Only include USA jobs
                    if country != "US" and country != "United States":
                        self.logger.debug("Skipping non-USA job: %s (state: %s, country: %s)", 
                                        job.get("jobOpeningName"), state, country)
                        continue

                    # Validate state
                    if state and state.upper() not in US_STATES:
                        self.logger.debug("Skipping job with unknown state: %s (%s)", 
                                        job.get("jobOpeningName"), state)
                        continue

                    parsed_job = self._parse_job(job, details, subdomain)
                    if parsed_job:
                        jobs.append(parsed_job)

                    # Rate limiting
                    if i < len(jobs_data) - 1:
                        await asyncio.sleep(0.5)

                except Exception as exc:
                    self.logger.debug("Error processing BambooHR job %s: %s", job.get("id"), exc)
                    continue

            self.logger.info("BambooHR scraped %d USA jobs for %s", len(jobs), subdomain)
            return jobs

        except Exception as exc:
            self.logger.error("BambooHR scrape failed for %s: %s", subdomain, exc)
            return []

    async def _fetch_company_info(self, base_url: str) -> dict | None:
        """Fetch and validate company info."""
        url = f"{base_url}/careers/company-info"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result")
        except Exception as exc:
            self.logger.debug("Failed to fetch BambooHR company info from %s: %s", url, exc)
        return None

    async def _fetch_job_listings(self, base_url: str) -> list[dict]:
        """Fetch all job listings from BambooHR API."""
        url = f"{base_url}/careers/list"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result", [])
        except Exception as exc:
            self.logger.debug("Failed to fetch BambooHR job listings from %s: %s", url, exc)
        return []

    async def _fetch_job_details(self, base_url: str, job_id: str) -> dict | None:
        """Fetch detailed information for a specific job."""
        url = f"{base_url}/careers/{job_id}/detail"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result", {}).get("jobOpening", {})
        except Exception as exc:
            self.logger.debug("Failed to fetch BambooHR job details from %s: %s", url, exc)
        return None

    def _parse_job(self, listing: dict, details: dict, subdomain: str) -> Job | None:
        """Parse job data from listing and details."""
        try:
            job_id = listing.get("id")
            if not job_id:
                return None

            title = listing.get("jobOpeningName", "Unknown")
            if not title:
                return None

            # Location info
            location_info = listing.get("atsLocation", {})
            city = location_info.get("city", "")
            state = location_info.get("state", "")
            location = f"{city}, {state}".strip(", ") if city or state else "Not Specified"

            # Workplace type mapping
            workplace_type = listing.get("locationType", "")
            workplace_map = {"0": "On-site", "1": "Remote", "2": "Hybrid"}
            workplace = workplace_map.get(workplace_type, "")

            # Description
            description = details.get("description", "")

            # Posted date
            posted_at = details.get("datePosted")

            # Apply URL
            apply_url = details.get("jobOpeningShareUrl", "")
            if not apply_url:
                apply_url = f"https://{subdomain}.bamboohr.com/careers/{job_id}"

            return Job(
                job_id=self.generate_job_id(self.ATS_NAME, self.company.name, str(job_id)),
                title=str(title)[:200],
                company=self.company.name,
                location=str(location),
                description=str(description),
                posted_at=posted_at,
                apply_url=str(apply_url),
                source_ats=self.ATS_NAME,
            )

        except Exception as exc:
            self.logger.debug("Error parsing BambooHR job: %s", exc)
            return None


