import asyncio
import aiohttp
import json

async def check_url(session, company):
    name = company.get("name")
    ats = company.get("ats_type")
    identifier = company.get("identifier")
    base_url = company.get("base_url")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if ats == "lever":
        url = f"https://api.lever.co/v0/postings/{identifier}?mode=json&limit=1"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "workday":
        if not base_url:
            return name, ats, "N/A", "Missing base_url"
        tenant, site = identifier.split("/", 1)
        url = f"{base_url.rstrip('/')}/wday/cxs/{tenant}/{site}/jobs"
        payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}
        async with session.post(url, json=payload, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "smartrecruiters":
        url = f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "jobvite":
        url = f"https://www.jobvite.com/CompanyJobs/Xml.aspx?c={identifier}"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "icims":
        if not base_url: return name, ats, "N/A", "Missing base_url"
        url = f"{base_url.rstrip('/')}/jobs/search?pr=0&in_iframe=1&format=json"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "taleo":
        if not base_url: return name, ats, "N/A", "Missing base_url"
        url = f"{base_url.rstrip('/')}/careersection/rest/jobboard/searchjobs?portal=1"
        payload = {"pageIndex": 1}
        async with session.post(url, json=payload, headers=headers) as resp:
            return name, ats, url, resp.status
    elif ats == "bamboohr":
        url = f"https://{identifier}.bamboohr.com/careers/list"
        async with session.get(url, headers=headers) as resp:
            return name, ats, url, resp.status
    else:
        return name, ats, "N/A", f"Unsupported ATS: {ats}"

async def main():
    with open("companies.json", "r") as f:
        data = json.load(f)
    
    companies = data.get("companies", [])
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_url(session, c) for c in companies]
        results = await asyncio.gather(*tasks)
        
        print(f"{'Company':<30} | {'ATS':<15} | {'Status':<10} | {'URL'}")
        print("-" * 100)
        for name, ats, url, status in results:
            print(f"{name:<30} | {ats:<15} | {status:<10} | {url}")

if __name__ == "__main__":
    asyncio.run(main())
