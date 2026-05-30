"""SmartRecruiters ATS scraper."""

from __future__ import annotations

import re
from app.models import Job
from app.scrapers.base import BaseScraper


class SmartRecruitersScraper(BaseScraper):
    """Scraper for SmartRecruiters career sites.

    SmartRecruiters public API:
        GET https://api.smartrecruiters.com/v1/companies/{companyId}/postings

    Identifier should be the SmartRecruiters company ID.
    """

    ATS_NAME = "smartrecruiters"
    BASE_URL = "https://api.smartrecruiters.com/v1/companies"

    async def scrape(self) -> list[Job]:
        """Fetch all jobs from SmartRecruiters."""
        company_id = self.company.identifier
        url = f"{self.BASE_URL}/{company_id}/postings"
        
        all_jobs: list[Job] = []
        offset = 0
        limit = 100
        
        while True:
            params = {"offset": offset, "limit": limit}
            data = await self._get(url, params=params)
            
            if not isinstance(data, dict):
                break
                
            content = data.get("content", [])
            if not content:
                break
                
            for raw in content:
                job = self._parse_job(raw)
                if job:
                    all_jobs.append(job)
            
            offset += len(content)
            total = data.get("totalNumber", 0)
            if offset >= total:
                break
                
        return all_jobs

    def _parse_job(self, raw: dict) -> Job | None:
        """Parse a single SmartRecruiters job object."""
        ext_id = raw.get("id")
        if not ext_id:
            return None
            
        location_obj = raw.get("location", {})
        city = location_obj.get("city", "")
        region = location_obj.get("region", "")
        country = location_obj.get("country", "") or ""
        # Only include if US
        if city and region:
            location = f"{city}, {region}"
        elif city:
            location = city
        else:
            location = country
        
        title = raw.get("name", "Unknown")
        dept = raw.get("department", {}).get("label", "") if raw.get("department") else ""
        job_function = raw.get("jobFunction", {}).get("label", "") if raw.get("jobFunction") else ""
        type_of_employment = raw.get("typeOfEmployment", {}).get("label", "") if raw.get("typeOfEmployment") else ""
        
        parts = [f"{title} at {self.company.name}."]
        if dept:
            parts.append(f"Department: {dept}.")
        if job_function:
            parts.append(f"Function: {job_function}.")
        if type_of_employment:
            parts.append(f"Employment type: {type_of_employment}.")
        if location:
            parts.append(f"Location: {location}.")
        description = " ".join(parts)
        
        # Correct SmartRecruiters public job URL
        apply_url = f"https://jobs.smartrecruiters.com/{self.company.identifier}/{ext_id}"
        
        return Job(
            job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
            title=title,
            company=self.company.name,
            location=location,
            description=description,
            posted_at=raw.get("releasedDate"),
            apply_url=apply_url,
            source_ats=self.ATS_NAME,
        )
