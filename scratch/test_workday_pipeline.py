"""End-to-end: scrape JC page -> enrich -> store in Redis -> read back from Redis."""
import asyncio, aiohttp
from app.models import CompanyConfig
from app.scrapers.workday import WorkdayScraper
from app.redis_client import redis_client


class DummyRL:
    def __call__(self, domain):
        class C:
            async def __aenter__(self): return None
            async def __aexit__(self, *a): return False
        return C()


async def main():
    await redis_client.connect()
    company = CompanyConfig(
        name="Johnson Controls", ats_type="workday",
        identifier="jci/JCI", base_url="https://jci.wd5.myworkdayjobs.com",
    )
    host = "https://jci.wd5.myworkdayjobs.com"; tenant, site = "jci", "JCI"
    async with aiohttp.ClientSession() as session:
        s = WorkdayScraper(company, session, redis=redis_client, rate_limiter=DummyRL())
        data = await s._post(
            f"{host}/wday/cxs/{tenant}/{site}/jobs",
            json_data={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        )
        postings = data["jobPostings"]
        jobs = []
        for raw in postings:
            job = s._parse_job(raw, host, site, "en-US")
            await s._enrich_description(job, raw, host, tenant, site)
            jobs.append(job)
        us_jobs = s.filter_us_jobs(jobs)

        # Clear any stale cached copies so we test a true fresh store round-trip
        for j in us_jobs:
            await redis_client.pool.delete(j.to_redis_key())
            await redis_client.pool.srem(f"company:{j.company_slug()}:jobs", j.job_id)

        stored = await redis_client.store_jobs(us_jobs)
        print(f"scraped={len(jobs)}  us={len(us_jobs)}  stored_in_redis={stored}")

        # Read back each stored job by ID through the real serve path (get_job)
        readback = [await redis_client.get_job(j.job_id) for j in us_jobs]
        with_desc = [j for j in readback if j and j.description]
        print(f"stored jobs read back={len(readback)}  with_description={len(with_desc)}")
        for j in with_desc[:5]:
            print(f"  desc_len={len(j.description):5d}  {j.title[:45]}")
        assert len(with_desc) == len(us_jobs), \
            f"only {len(with_desc)}/{len(us_jobs)} have descriptions after round-trip"
        print("PASS - all stored jobs serve full descriptions via Redis round-trip")


if __name__ == "__main__":
    asyncio.run(main())
