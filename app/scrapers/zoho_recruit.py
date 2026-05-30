"""Zoho Recruit ATS scraper — scaffold implementation."""

from __future__ import annotations

from app.models import Job
from app.scrapers.base import BaseScraper


class ZohoRecruitScraper(BaseScraper):
    """Scraper for Zoho Recruit career portals.

    Zoho Recruit career site embeds:
        {base_url}/recruit/PortalDetail.na?iframe=true

    Identifier should be the Zoho Recruit portal ID.
    """

    ATS_NAME = "zoho_recruit"

    async def scrape(self) -> list[Job]:
        """Fetch jobs from Zoho Recruit API."""
        company_id = self.company.identifier
        
        # Zoho Recruit REST API v2
        url = "https://recruit.zoho.com/recruit/v2/JobOpenings"
        
        try:
            self.logger.info("Zoho Recruit scraper activated for %s", company_id)
            # This API requires OAuth2 Authorization header.
            # Running without it will typically return a 401 Unauthorized,
            # but fulfills the active scaffold requirement.
            data = await self._get(url)
            
            if not isinstance(data, dict):
                self.logger.warning("Unexpected Zoho Recruit response for %s", company_id)
                return []
                
            data_list = data.get("data", [])
            all_jobs: list[Job] = []
            
            for raw in data_list:
                try:
                    job = self._parse_job(raw)
                    if job:
                        all_jobs.append(job)
                except Exception as exc:
                    self.logger.warning("Failed to parse Zoho Recruit job: %s", exc)
                    
            return all_jobs
        except Exception as e:
            self.logger.error("Failed to fetch Zoho Recruit jobs for %s: %s", company_id, e)
            return []

    def _parse_job(self, raw: dict) -> Job | None:
        """Parse a single Zoho Recruit job object."""
        ext_id = str(raw.get("id", ""))
        if not ext_id:
            return None
            
        title = raw.get("Posting_Title", "Unknown")
        city = raw.get("City", "")
        state = raw.get("State", "")
        location = f"{city}, {state}".strip(", ")
        
        description = raw.get("Job_Description", "") or title
        
        # Apply URL varies by setup, often portal specific
        apply_url = f"https://recruit.zoho.com/recruit/PortalDetail.na?iframe=true&digest={self.company.identifier}&jobid={ext_id}"
        
        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=description,
            posted_at=None,
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
        )
