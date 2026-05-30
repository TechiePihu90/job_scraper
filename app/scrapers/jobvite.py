"""Jobvite ATS scraper."""

from __future__ import annotations

import re
import html
from bs4 import BeautifulSoup
from app.models import Job
from app.scrapers.base import BaseScraper


class JobviteScraper(BaseScraper):
    """Scraper for Jobvite career sites.

    First tries the public API: https://api.jobvite.com/v1/jobs?company={companySlug}
    Falls back to HTML scraping if API fails.

    Identifier should be the Jobvite company slug.
    """

    ATS_NAME = "jobvite"

    async def scrape(self) -> list[Job]:
        """Fetch jobs from Jobvite using API first, then HTML fallback."""
        company_slug = self.company.identifier
        
        # Try the public JSON API first
        try:
            jobs = await self._scrape_api(company_slug)
            if jobs:
                self.logger.info("Jobvite API returned %d jobs for %s", len(jobs), company_slug)
                return jobs
        except Exception as exc:
            self.logger.debug("Jobvite API failed for %s: %s", company_slug, exc)
        
        # Fallback to HTML scraping if API fails
        try:
            # Try multiple URL patterns for Jobvite
            urls_to_try = [
                f"https://{company_slug}.jobvite.com/careers",
                f"https://{company_slug}.jobvite.com/jobs",
                f"https://{company_slug}.jobvite.com",
                f"https://jobs.jobvite.com/{company_slug}",
                f"https://jobs.jobvite.com/{company_slug}/jobs",
            ]
            
            for url in urls_to_try:
                try:
                    self.logger.debug("Trying Jobvite HTML scrape from: %s", url)
                    html_content = await self._get(url)
                    if html_content and isinstance(html_content, str):
                        jobs = self._parse_career_page(html_content)
                        if jobs:
                            self.logger.info("Jobvite HTML scraping returned %d jobs from %s", len(jobs), url)
                            return jobs
                except Exception as e:
                    self.logger.debug("Jobvite HTML scrape failed for %s: %s", url, str(e)[:100])
                    continue
                    
        except Exception as exc:
            self.logger.debug("Jobvite HTML scraping failed for %s: %s", company_slug, exc)
        
        self.logger.warning("No jobs found for Jobvite company %s via API or HTML scraping", company_slug)
        return []

    async def _scrape_api(self, company_slug: str) -> list[Job]:
        """Fetch jobs from Jobvite public API."""
        url = f"https://api.jobvite.com/v1/jobs?company={company_slug}"
        try:
            data = await self._get(url)
            if not isinstance(data, dict):
                self.logger.debug("Jobvite API returned non-dict response: %s", type(data))
                return []
            
            jobs = []
            job_list = data.get("jobs", [])
            if not job_list and "jobs" not in data:
                self.logger.debug("No jobs field in Jobvite API response. Keys: %s", list(data.keys())[:5])
                return []
                
            for item in job_list:
                job = self._parse_api_job(item)
                if job:
                    jobs.append(job)
            
            if jobs:
                self.logger.info("Jobvite API returned %d jobs", len(jobs))
            return jobs
        except Exception as exc:
            error_msg = str(exc)
            if "404" in error_msg or "not found" in error_msg.lower():
                self.logger.debug("Jobvite API not found (404) for %s - company may not exist", company_slug)
            else:
                self.logger.debug("Error fetching Jobvite API: %s", exc)
            return []

    def _parse_api_job(self, item: dict) -> Job | None:
        """Parse a job from Jobvite API response."""
        try:
            ext_id = item.get("id") or item.get("jobId")
            if not ext_id:
                return None
            
            title = item.get("title", "Unknown")
            location = item.get("location", "")
            description = item.get("description", "") or item.get("jobDescription", "") or title
            
            # Clean description
            description = self.normalize_text(description)
            
            apply_url = item.get("apply_url") or item.get("applyUrl")
            if not apply_url:
                apply_url = f"https://{self.company.identifier}.jobvite.com/job/{ext_id}"
            
            return Job(
                job_id=self.generate_job_id(self.ATS_NAME, self.company.name, str(ext_id)),
                title=title,
                company=self.company.name,
                location=location,
                description=description,
                posted_at=None,
                apply_url=apply_url,
                source_ats=self.ATS_NAME,
            )
        except Exception as exc:
            self.logger.debug("Error parsing Jobvite API job: %s", exc)
            return None

    def _parse_career_page(self, html_content: str) -> list[Job]:
        """Parse Jobvite career page HTML to extract jobs using flexible selectors."""
        jobs = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Use flexible selectors similar to reference code
            # Try multiple patterns: article tags, elements with job class, job links
            job_elements = soup.select("article")
            if not job_elements:
                job_elements = soup.select("li[class*='job']")
            if not job_elements:
                job_elements = soup.select("a[href*='/job/']")
            if not job_elements:
                job_elements = soup.select("div[class*='job-posting'], div[class*='job-card'], div[data-job-id]")
                
            self.logger.debug("Found %d potential job elements for Jobvite", len(job_elements))
            
            for job_elem in job_elements:
                job = self._parse_job_element(job_elem)
                if job:
                    jobs.append(job)
                    
        except Exception as exc:
            self.logger.debug("Error parsing Jobvite HTML: %s", exc)
            
        return jobs

    def _parse_job_element(self, elem) -> Job | None:
        """Parse a single job element from Jobvite HTML using flexible selectors."""
        try:
            # Extract job ID from multiple sources
            ext_id = elem.get("data-job-id") or elem.get("data-id")
            
            if not ext_id:
                # Try to extract from href attribute
                href = elem.get("href", "")
                if not href:
                    # Look for nested link
                    link_elem = elem.find("a", href=True)
                    if link_elem:
                        href = link_elem.get("href", "")
                
                if "/job/" in href:
                    ext_id = href.split("/job/")[-1].split("?")[0].split("/")[0]
            
            if not ext_id:
                return None
            
            # Extract title using flexible selectors (h3, h2, a with title class, etc.)
            title_elem = elem.select_one("h3") or elem.select_one("h2") or \
                         elem.select_one("a[class*='title']") or elem.find("a")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            
            if not title or title == "Unknown":
                return None
            
            # Extract location using flexible selectors
            location_elem = elem.select_one("[class*='location']") or \
                           elem.select_one("address") or \
                           elem.find("span", class_=re.compile(r"location", re.I))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Extract department/team if available
            dept_elem = elem.select_one("[class*='department']") or \
                       elem.select_one("[class*='team']")
            department = dept_elem.get_text(strip=True) if dept_elem else ""
            
            # Build description from available elements
            desc_elem = elem.select_one("p") or \
                       elem.select_one("[class*='description']") or \
                       elem.select_one("[class*='summary']")
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            if not description:
                description = f"{title} at {self.company.name}"
            
            # Clean description
            description = self.normalize_text(description)
            
            # Build apply URL
            apply_url = elem.get("href") if elem.name == "a" else None
            if not apply_url:
                link_elem = elem.find("a", href=True)
                if link_elem:
                    apply_url = link_elem.get("href")
            
            if apply_url and not apply_url.startswith("http"):
                apply_url = f"https://{self.company.identifier}.jobvite.com{apply_url}"
            elif not apply_url:
                apply_url = f"https://{self.company.identifier}.jobvite.com/job/{ext_id}"
            
            return Job(
                job_id=self.generate_job_id(self.ATS_NAME, self.company.name, str(ext_id)),
                title=title,
                company=self.company.name,
                location=location,
                description=description,
                posted_at=None,
                apply_url=apply_url,
                source_ats=self.ATS_NAME,
            )
        except Exception as exc:
            self.logger.debug("Error parsing Jobvite job element: %s", exc)
            return None
