import re
import html
import asyncio
from bs4 import BeautifulSoup
from app.models import Job
from app.scrapers.base import BaseScraper

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ClearCompanyScraper(BaseScraper):
    """Scraper for ClearCompany career sites using Playwright.

    ClearCompany career page (HTML scraping):
        https://{identifier}.clearcompany.com/careers/jobs

    Uses Playwright to render JavaScript-heavy pages and extract job listings.
    Identifier should be the ClearCompany client slug.
    """

    ATS_NAME = "clearcompany"

    async def scrape(self) -> list[Job]:
        """Fetch jobs from ClearCompany using Playwright for JS rendering."""
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error("Playwright not installed. Install with: pip install playwright")
            return []

        company_id = self.company.identifier
        url = f"https://{company_id}.clearcompany.com/careers/jobs"
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                self.logger.info("Loading ClearCompany careers page: %s", url)
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout loading %s, continuing with partial content", url)

                # Wait for job listings
                try:
                    await page.wait_for_selector(".job-listing, .job-card, [data-job-id], .position-card", timeout=5000)
                except:
                    self.logger.debug("No job selectors found, attempting extraction")

                # Scroll and load more jobs
                for _ in range(5):
                    try:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1)
                    except:
                        break

                html_content = await page.content()
                await browser.close()

                all_jobs = self._parse_career_page(html_content)
                self.logger.info("ClearCompany scraped %d jobs for %s", len(all_jobs), company_id)
                return all_jobs
            
        except Exception as e:
            self.logger.debug("Failed to fetch ClearCompany jobs for %s: %s", company_id, e)
            return []

    def _parse_career_page(self, html_content: str) -> list[Job]:
        """Parse ClearCompany career page HTML to extract jobs."""
        jobs = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            job_containers = []

            # Strategy 1: Find elements with data attributes
            for tag in soup.find_all(["div", "li", "article"]):
                data_id = tag.get("data-job-id") or tag.get("data-id")
                if data_id:
                    job_containers.append(tag)

            # Strategy 2: Look for common class patterns
            if not job_containers:
                for tag in soup.find_all(["div", "li", "article"]):
                    class_str = " ".join(tag.get("class", []))
                    if any(pattern in class_str.lower() for pattern in ["job", "position", "posting", "opening", "listing"]):
                        job_containers.append(tag)

            # Strategy 3: Find links matching job patterns
            if not job_containers:
                job_containers = soup.find_all("a", href=re.compile(r"/careers/jobs/\d+|/job/", re.I))

            # Remove duplicates
            seen = set()
            unique_containers = []
            for container in job_containers:
                html_str = str(container)
                if html_str not in seen:
                    seen.add(html_str)
                    unique_containers.append(container)

            for container in unique_containers:
                job = self._parse_job_element(container)
                if job:
                    jobs.append(job)

        except Exception as exc:
            self.logger.debug("Error parsing ClearCompany HTML: %s", exc)

        return jobs

    def _parse_job_element(self, elem) -> Job | None:
        """Parse a single ClearCompany job from element."""
        try:
            # Extract job ID from href or data attribute
            ext_id = elem.get("data-job-id") or elem.get("data-id")
            if not ext_id:
                href = elem.get("href", "")
                if "/job/" in href:
                    ext_id = href.split("/job/")[-1].split("?")[0]
                elif "/careers/jobs/" in href:
                    ext_id = href.split("/careers/jobs/")[-1].split("/")[0]
            if not ext_id:
                return None

            # Extract title
            title_elem = elem.find("h2") or elem.find("h3") or elem.find("a", class_=re.compile(r"title|name", re.I))
            title = title_elem.get_text(strip=True) if title_elem else None
            if not title:
                title = elem.get_text(strip=True).split("\n")[0] or "Unknown"
            
            # Extract location
            location_elem = elem.find("span", class_=re.compile(r"location|city|state|region", re.I))
            if location_elem:
                location = location_elem.get_text(strip=True)
            else:
                # Try to find in text
                text = elem.get_text()
                location_match = re.search(r"([A-Z]{2})|([A-Z][a-z]+,\s*[A-Z]{2})", text)
                location = location_match.group(0) if location_match else ""
            
            # Extract description
            desc_elem = elem.find("p") or elem.find("div", class_=re.compile(r"description|summary", re.I))
            description = desc_elem.get_text(strip=True) if desc_elem else title
            
            # Clean HTML entities
            description = self.normalize_text(description)
            
            # Build apply URL
            apply_url = elem.get("href") or ""
            if not apply_url or not apply_url.startswith("http"):
                apply_url = f"https://{self.company.identifier}.clearcompany.com/careers/jobs/{ext_id}"
            
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
            self.logger.debug("Error parsing ClearCompany job element: %s", exc)
            return None
