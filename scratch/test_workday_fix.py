"""Thorough test of the Workday description-enrichment fix against the live API."""
import asyncio, aiohttp
from app.models import CompanyConfig
from app.scrapers.workday import WorkdayScraper


class DummyRL:
    def __call__(self, domain):
        class C:
            async def __aenter__(self): return None
            async def __aexit__(self, *a): return False
        return C()


async def main():
    company = CompanyConfig(
        name="Johnson Controls", ats_type="workday",
        identifier="jci/JCI", base_url="https://jci.wd5.myworkdayjobs.com",
    )
    host = "https://jci.wd5.myworkdayjobs.com"
    tenant, site = "jci", "JCI"
    async with aiohttp.ClientSession() as session:
        s = WorkdayScraper(company, session, redis=None, rate_limiter=DummyRL())
        data = await s._post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json_data={"appliedFacets": {}, "limit": 8, "offset": 0, "searchText": ""},
        )
        postings = data["jobPostings"]
        print(f"search OK: {len(postings)} postings, total={data.get('total')}\n")
        empty = 0
        for raw in postings:
            job = s._parse_job(raw, host, site, "en-US")
            await s._enrich_description(job, raw, host, tenant, site)
            flag = "OK " if job.description else "!! EMPTY"
            print(f"  [{flag}] desc_len={len(job.description):5d}  {job.title[:45]}")
            if not job.description:
                empty += 1
        print(f"\nRESULT: {len(postings)-empty}/{len(postings)} enriched, {empty} empty")
        assert empty == 0, f"{empty} jobs STILL have empty descriptions"
        print("PASS ✅ — all Workday descriptions populated")


if __name__ == "__main__":
    asyncio.run(main())
