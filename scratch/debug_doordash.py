
import asyncio
import aiohttp
import json
from app.scrapers.greenhouse import GreenhouseScraper
from app.models import CompanyConfig
from app.redis_client import redis_client
from app.utils.rate_limiter import AsyncRateLimiter

async def debug_doordash():
    company = CompanyConfig(name="DoorDash", ats_type="greenhouse", identifier="doordash")
    async with aiohttp.ClientSession() as session:
        rate_limiter = AsyncRateLimiter(rate=5)
        scraper = GreenhouseScraper(company=company, session=session, redis=redis_client, rate_limiter=rate_limiter)
        
        # Test the raw GET
        url = f"https://boards-api.greenhouse.io/v1/boards/doordash/jobs"
        async with session.get(url) as resp:
            print(f"DoorDash RAW GET status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Total jobs in Greenhouse for DoorDash: {len(data.get('jobs', []))}")
            else:
                print(f"Error: {await resp.text()}")

if __name__ == "__main__":
    asyncio.run(debug_doordash())
