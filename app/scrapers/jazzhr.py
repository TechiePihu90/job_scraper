"""JazzHR ATS scraper - fetches jobs from JazzHR job boards."""

from __future__ import annotations

import re
import html
import asyncio
from bs4 import BeautifulSoup
from app.models import Job
from app.scrapers.base import BaseScraper
from app.utils.location import is_us_location


class JazzHRScraper(BaseScraper):
    """Scraper for JazzHR job boards.

    JazzHR career page (HTML scraping):
        https://{company_slug}.applytojob.com/apply

    Uses simple requests + BeautifulSoup for reliable HTML parsing.
    Identifier should be the JazzHR company slug.
    """

    ATS_NAME = "jazzhr"

    async def scrape(self) -> list[Job]:
        """Fetch jobs from JazzHR company portal."""
        company_slug = self.company.identifier
        base_url = f"https://{company_slug}.applytojob.com/apply"
        
        try:
            # Fetch the job listings page
            html_content = await self._get(base_url)
            
            if not isinstance(html_content, str):
                self.logger.warning("Unexpected response type from JazzHR")
                return []
            
            # Parse job listings from the page
            jobs = await self._parse_job_listings(html_content)
            self.logger.info("JazzHR scraped %d jobs from %s", len(jobs), company_slug)
            return jobs
            
        except Exception as exc:
            self.logger.warning("JazzHR scrape failed for %s: %s", company_slug, exc)
            return []

    async def _parse_job_listings(self, html_content: str) -> list[Job]:
        """Parse job listings page and fetch details for each job."""
        jobs = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Primary selector: list-group structure (as per reference code)
            job_items = soup.select('li.list-group-item')
            
            self.logger.debug("Found %d job items in listings page", len(job_items))
            
            for idx, item in enumerate(job_items):
                try:
                    job = await self._parse_job_item(item, idx)
                    if job:
                        jobs.append(job)
                    
                    # Rate limiting - add delay between requests
                    if idx < len(job_items) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as exc:
                    self.logger.debug("Failed to parse job item %d: %s", idx, exc)
                    continue
            
        except Exception as exc:
            self.logger.debug("Error parsing JazzHR job listings: %s", exc)
        
        return jobs

    async def _parse_job_item(self, item, index: int) -> Job | None:
        """Parse a single job item and fetch full details."""
        try:
            # Extract job URL and title
            title_elem = item.select_one('h4.list-group-item-heading a')
            if not title_elem:
                title_elem = item.select_one('a[href*="/apply/"]')
            
            if not title_elem:
                return None
            
            job_url = title_elem.get('href', '')
            title = title_elem.get_text(strip=True)
            
            if not job_url or not title:
                return None
            
            # Normalize URL (HTTP to HTTPS)
            if job_url.startswith('http://'):
                job_url = job_url.replace('http://', 'https://')
            
            # Make absolute URL
            if not job_url.startswith('http'):
                company_slug = self.company.identifier
                job_url = f"https://{company_slug}.applytojob.com{job_url}"
            
            # Extract location and department from listing
            info_items = item.select('ul.list-inline.list-group-item-text li')
            location = info_items[0].get_text(strip=True) if len(info_items) > 0 else ""
            department = info_items[1].get_text(strip=True) if len(info_items) > 1 else ""
            
            # Extract job ID from URL
            job_id_match = re.search(r'/apply/([A-Za-z0-9]{8,})', job_url)
            ext_id = job_id_match.group(1) if job_id_match else None
            
            if not ext_id:
                return None
            
            # Filter for US locations
            if location and not is_us_location(location):
                self.logger.debug("Skipping non-US job: %s at %s", title, location)
                return None
            
            # Fetch individual job details
            try:
                details = await self._fetch_job_details(job_url)
            except Exception as exc:
                self.logger.debug("Failed to fetch job details from %s: %s", job_url, exc)
                details = {}
            
            # Merge details
            if details:
                title = details.get('title', title)
                location = details.get('location', location)
                description = details.get('description', '')
            else:
                description = ''
            
            # Build job object
            return Job(
                job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
                title=title[:200],
                company=self.company.name,
                location=location,
                description=description,
                posted_at=None,
                apply_url=job_url,
                source_ats=self.ATS_NAME,
            )
            
        except Exception as exc:
            self.logger.debug("Error parsing job item: %s", exc)
            return None

    async def _fetch_job_details(self, job_url: str) -> dict:
        """Fetch and parse individual job details page."""
        details = {}
        try:
            html_content = await self._get(job_url)
            
            if not isinstance(html_content, str):
                return details
            
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Title
            title_elem = soup.select_one('div.job-header h1, h1')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # Location
            location_elem = soup.select_one("div.job-attributes-container div[title='Location']")
            if location_elem:
                details['location'] = location_elem.get_text(strip=True)
            
            # Description
            desc_elem = soup.select_one('#job-description, .job-details .description')
            if desc_elem:
                raw_desc = desc_elem.get_text(strip=True)
                details['description'] = self.normalize_text(raw_desc)
            
            # Compensation
            comp_elem = soup.select_one(
                "div.job-attributes-container div[title='Compensation'], "
                "div.job-attributes-container div[title='Salary'], "
                "#resumator-job-salary"
            )
            if comp_elem:
                details['compensation'] = comp_elem.get_text(strip=True)
            elif details.get('description'):
                # Search for salary in description
                salary_match = re.search(
                    r'\$[\d,]+(?:\s*-\s*\$?[\d,]+)?(?:\s*(?:per|/)\s*\w+)?',
                    details['description']
                )
                if salary_match:
                    details['compensation'] = salary_match.group()
            
        except Exception as exc:
            self.logger.debug("Error fetching job details from %s: %s", job_url, exc)
        
        return details
