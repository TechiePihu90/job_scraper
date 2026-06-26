import asyncio
import aiohttp

from app.models import CompanyConfig
from app.scrapers.icims import ICIMSScraper
from app.utils.rate_limiter import AsyncRateLimiter


async def test_icims():
    company = CompanyConfig(
        name="Healthcare Services Group",
        ats_type="icims",
        identifier="healthcareservicesgroup",
        base_url="https://careers-hcsgcorp.icims.com/",
    )
    async with aiohttp.ClientSession() as session:
        rate_limiter = AsyncRateLimiter(rate=5)
        scraper = ICIMSScraper(
            company=company,
            session=session,
            rate_limiter=rate_limiter,
        )
        print(f"Scraping jobs for {company.name}...")
        jobs = await scraper.scrape()
        print("\nVerification Results:")
        print(f"Total jobs fetched: {len(jobs)}")

        if jobs:
            print("\nFirst 5 jobs details:")
            for idx, job in enumerate(jobs[:5], 1):
                print(f"\nJob {idx}:")
                print(f"  ID: {job.job_id}")
                print(f"  Title: {job.title}")
                print(f"  Location: {job.location}")
                print(f"  Apply URL: {job.apply_url}")
                print(f"  Description: {job.description[:150]}...")
        else:
            print("No jobs fetched.")


if __name__ == "__main__":
    asyncio.run(test_icims())
