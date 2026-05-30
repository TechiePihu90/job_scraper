
import asyncio
import aiohttp
from app.scrapers.smartrecruiters import SmartRecruitersScraper
from app.models import CompanyConfig
from app.redis_client import redis_client
from app.utils.rate_limiter import AsyncRateLimiter

async def find_working_sr():
    ids = ["Skechers", "skechers", "visa", "Visa", "publicisgroupe", "Twitter", "square", "Square"]
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        rate_limiter = AsyncRateLimiter(rate=2)
        for identifier in ids:
            company = CompanyConfig(name=identifier, ats_type="smartrecruiters", identifier=identifier)
            scraper = SmartRecruitersScraper(company=company, session=session, redis=redis_client, rate_limiter=rate_limiter)
            try:
                jobs = await scraper.scrape()
                print(f"ID: {identifier} -> {len(jobs)} jobs")
            except Exception as e:
                print(f"ID: {identifier} -> Error: {e}")

if __name__ == "__main__":
    asyncio.run(find_working_sr())
