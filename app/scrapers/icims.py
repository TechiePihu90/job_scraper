"""iCIMS ATS scraper."""

from __future__ import annotations

import asyncio
import re
from playwright.async_api import async_playwright, Page

from app.models import Job
from app.scrapers.base import BaseScraper


class ICIMSScraper(BaseScraper):
    """Scraper for iCIMS career portals using Playwright.

    Uses Playwright for reliable JavaScript rendering and proper selector-based job extraction.
    Handles pagination automatically and extracts job details from iCIMS job board.
    """

    ATS_NAME = "icims"
    PAGE_SIZE = 20

    async def scrape(self) -> list[Job]:
        """Fetch all jobs from the iCIMS portal with pagination using Playwright."""
        base = self.company.base_url
        if not base:
            self.logger.error("iCIMS requires base_url")
            return []

        all_jobs: list[Job] = []
        page_num = 0

        async with async_playwright() as p:
            browser = None
            try:
                # Launch with a few common flags to reduce headless detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )

                # Use a dedicated context with a real-looking user-agent
                context = await browser.new_context(user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ))

                # Basic anti-detection init script
                await context.add_init_script("""
                // Pass the webdriver check
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                // Languages
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                // Plugins
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                """)

                while True:
                    # iCIMS page index starts at 0
                    url = f"{base.rstrip('/')}/jobs/search?pr={page_num}"
                    self.logger.info("iCIMS page %d: %s", page_num, url)

                    try:
                        page = await context.new_page()
                        # Add a lightweight init on the page level as well
                        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        
                        # Wait for job listings to load; detect human-verification pages
                        try:
                            # quick check: page title can indicate a block (e.g., "Human Verification")
                            title = (await page.title()).lower() or ""
                            if "human verification" in title or "verify" in title:
                                self.logger.error("iCIMS blocked by human verification on %s", url)
                                await page.close()
                                break

                            await page.wait_for_selector(".iCIMS_JobsTable .row", timeout=10000)
                        except Exception:
                            self.logger.debug("No job listings found on page %d", page_num)
                            await page.close()
                            break

                        jobs_on_page = await self._parse_page(page, base)
                        await page.close()
                        
                        if not jobs_on_page:
                            self.logger.info("No jobs parsed on page %d, ending pagination.", page_num)
                            break

                        for job in jobs_on_page:
                            all_jobs.append(job)

                        # If we got fewer jobs than page size, we reached the end
                        if len(jobs_on_page) < self.PAGE_SIZE:
                            self.logger.info("Parsed %d jobs (less than page size %d), ending.", len(jobs_on_page), self.PAGE_SIZE)
                            break

                        page_num += 1

                    except Exception as exc:
                        self.logger.error("iCIMS page fetch failed: %s", exc)
                        if page:
                            await page.close()
                        break

            finally:
                try:
                    if context:
                        await context.close()
                except Exception:
                    pass
                if browser:
                    await browser.close()

        self.logger.info("iCIMS scraped %d total jobs for %s", len(all_jobs), self.company.name)
        return all_jobs

    async def _parse_page(self, page: Page, base: str) -> list[Job]:
        """Parse jobs from iCIMS page using proper selectors."""
        try:
            # Extract job data using Playwright's evaluate
            jobs_data = await page.evaluate("""(() => {
                const jobs = [];
                document.querySelectorAll(".iCIMS_JobsTable .row").forEach(row => {
                    const titleElem = row.querySelector(".iCIMS_JobTitle a");
                    const locationElem = row.querySelector(".iCIMS_JobLocation");
                    const categoryElem = row.querySelector(".iCIMS_JobCategory");
                    
                    const title = titleElem?.textContent?.trim();
                    const location = locationElem?.textContent?.trim();
                    const category = categoryElem?.textContent?.trim();
                    const link = titleElem?.getAttribute("href");
                    
                    if (title && link) {
                        jobs.push({
                            title,
                            location: location || "",
                            category: category || "",
                            link
                        });
                    }
                });
                return jobs;
            })()""")
            
            parsed_jobs: list[Job] = []
            
            for item in jobs_data:
                try:
                    title = item.get("title", "").strip()
                    location = item.get("location", "").strip()
                    category = item.get("category", "").strip()
                    link = item.get("link", "").strip()
                    
                    if not title or not link:
                        continue
                    
                    # Extract job ID from URL
                    job_id_match = re.search(r'/jobs/(\d+)/', link)
                    ext_id = job_id_match.group(1) if job_id_match else None
                    
                    if not ext_id:
                        continue
                    
                    # Build full apply URL
                    if not link.startswith('http'):
                        apply_url = base.rstrip('/') + link if link.startswith('/') else base.rstrip('/') + '/' + link
                    else:
                        apply_url = link
                    
                    # Use title as description for now (we can fetch full details later if needed)
                    description = f"{title}. Location: {location}" if location else title
                    if category:
                        description += f". Category: {category}"
                    
                    # store full description
                    
                    job = Job(
                        job_id=self.generate_job_id(self.ATS_NAME, self.company.name, ext_id),
                        title=title,
                        company=self.company.name,
                        location=location,
                        description=description,
                        posted_at=None,
                        apply_url=apply_url,
                        source_ats=self.ATS_NAME,
                    )
                    parsed_jobs.append(job)
                    
                except Exception as exc:
                    self.logger.debug("Failed to parse individual job: %s", exc)
            
            return parsed_jobs
            
        except Exception as exc:
            self.logger.error("Failed to evaluate page: %s", exc)
            return []
