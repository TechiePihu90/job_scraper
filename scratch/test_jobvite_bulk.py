import asyncio
import json
import aiohttp
from app.models import CompanyConfig
from app.scrapers.jobvite import JobviteScraper

class DummyRL:
    def __call__(self, domain):
        class C:
            async def __aenter__(self): return None
            async def __aexit__(self, *a): return False
        return C()

async def probe(company):
    async with aiohttp.ClientSession() as session:
        # convert dict to CompanyConfig model
        cfg = CompanyConfig(**company) if not isinstance(company, CompanyConfig) else company
        s = JobviteScraper(cfg, session, redis=None, rate_limiter=DummyRL())
        try:
            jobs = await s.scrape()
            return company['name'], company['identifier'], len(jobs)
        except Exception as e:
            return company['name'], company['identifier'], f"error: {e}"

async def main():
    with open('companies.json') as f:
        data = json.load(f)
    companies = [c for c in data.get('companies', []) if c.get('ats_type')=='jobvite']
    results = []
    for c in companies:
        name, ident, count = await probe(c)
        print(f"{name:40} | {ident:25} | {count}")

if __name__ == '__main__':
    asyncio.run(main())
