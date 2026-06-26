"""End-to-end: scrape JC page -> enrich -> store in database -> read back from database."""
import asyncio
import aiohttp

from app.models import CompanyConfig
from app.scrapers.workday import WorkdayScraper


class DummyRL:
    def __call__(self, domain):
        class C:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *a):
                return False

        return C()


async def main():
    company = CompanyConfig(
        name="Johnson Controls",
        ats_type="workday",
        identifier="jci/JCI",
        base_url="https://jci.wd5.myworkdayjobs.com",
    )
    host = "https://jci.wd5.myworkdayjobs.com"
    tenant, site = "jci", "JCI"
    async with aiohttp.ClientSession() as session:
        s = WorkdayScraper(company, session, rate_limiter=DummyRL())
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
        print(f"scraped={len(jobs)}  us={len(us_jobs)}")
        for job in us_jobs[:5]:
            print(f"  {job.title[:45]}")


if __name__ == "__main__":
    asyncio.run(main())
