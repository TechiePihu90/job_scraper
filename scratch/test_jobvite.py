import asyncio
import aiohttp
from app.models import CompanyConfig
from app.scrapers.jobvite import JobviteScraper

class DummyRL:
    def __call__(self, domain):
        class C:
            async def __aenter__(self): return None
            async def __aexit__(self, *a): return False
        return C()

async def main():
    company = CompanyConfig(name="TiVo", ats_type="jobvite", identifier="tivo")
    async with aiohttp.ClientSession() as session:
        s = JobviteScraper(company, session, redis=None, rate_limiter=DummyRL())
        jobs = await s.scrape()
        print(f"scraped={len(jobs)}")
        for j in jobs[:10]:
            print(j.title, j.location, j.apply_url)

if __name__ == '__main__':
    asyncio.run(main())
