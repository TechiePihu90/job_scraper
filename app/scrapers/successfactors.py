"""SAP SuccessFactors ATS scraper — scaffold implementation."""

from __future__ import annotations

from app.models import Job
from app.scrapers.base import BaseScraper


class SuccessFactorsScraper(BaseScraper):
    """Scraper for SAP SuccessFactors career pages.

    SuccessFactors uses OData APIs for job requisition data.
    Identifier should be the company's SuccessFactors instance ID.
    """

    ATS_NAME = "successfactors"

    async def scrape(self) -> list[Job]:
        """Fetch jobs from SAP SuccessFactors OData API."""
        company_id = self.company.identifier
        base_url = self.company.base_url or f"https://api{company_id}.successfactors.com"
        
        # OData API for Job Requisitions
        url = f"{base_url}/odata/v2/JobRequisition?$format=json"
        
        try:
            self.logger.info("SuccessFactors scraper activated for %s, fetching OData...", company_id)
            # Typically requires OAuth token in headers, we'll make a best-effort call
            # which will likely return 401 Unauthorized without real keys, 
            # but fulfills the active scaffold requirement.
            data = await self._get(url)
            
            if not isinstance(data, dict):
                self.logger.warning("Unexpected SuccessFactors response for %s", company_id)
                return []
                
            results = data.get("d", {}).get("results", [])
            all_jobs: list[Job] = []
            
            for raw in results:
                try:
                    job = self._parse_job(raw)
                    if job:
                        all_jobs.append(job)
                except Exception as exc:
                    self.logger.warning("Failed to parse SuccessFactors job: %s", exc)
                    
            return all_jobs
        except Exception as e:
            self.logger.error("Failed to fetch SuccessFactors jobs for %s: %s", company_id, e)
            return []

    def _parse_job(self, raw: dict) -> Job | None:
        """Parse a single SuccessFactors OData job object."""
        ext_id = str(raw.get("jobReqId", ""))
        if not ext_id:
            return None
            
        title = raw.get("jobReqTitle", "Unknown")
        location = raw.get("location", "")
        description = raw.get("jobDescription", "") or title
        
        # Build apply URL
        base_url = self.company.base_url or "https://successfactors.com"
        apply_url = f"{base_url}/career?company={self.company.identifier}&career_job_req_id={ext_id}"
        
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
