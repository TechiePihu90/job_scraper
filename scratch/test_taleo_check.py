import asyncio
import aiohttp
import json

async def check_taleo_company(session, name, base_url, portal_id):
    url = f"{base_url.rstrip('/')}/careersection/rest/jobboard/searchjobs?portal={portal_id}"
    payload = {
        "multilineEnabled": False,
        "sortingSelection": {"fieldId": "post_date", "sortOrder": 1},
        "fieldData": {"fields": {"keyword": "", "location": -1, "category": -1}, "valid": True},
        "filterSelection": {"fieldData": {"fields": {}, "valid": True}, "filterEntries": []},
        "pageIndex": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{base_url}/careersection/2/jobsearch.ftl",
        "tz": "GMT+05:30",
    }
    try:
        async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
            status = resp.status
            if status == 200:
                data = await resp.json()
                total = data.get("totalCount", 0)
                requisitions = len(data.get("requisitionList", []))
                return f"[SUCCESS] {name} ({portal_id}): status {status}, totalCount {total}, current_page_jobs {requisitions}"
            else:
                text = await resp.text()
                return f"[ERROR] {name} ({portal_id}): status {status}, response: {text[:200]}"
    except Exception as e:
        return f"[EXCEPTION] {name} ({portal_id}): {e}"

async def main():
    companies = [
        {"name": "Starbucks", "base_url": "https://starbucks.taleo.net", "portal_id": "starbucks"},
        {"name": "Nike", "base_url": "https://nike.taleo.net", "portal_id": "nike"},
        {"name": "Disney", "base_url": "https://disney.taleo.net", "portal_id": "disney"},
        {"name": "Deloitte", "base_url": "https://deloitte.taleo.net", "portal_id": "deloitte"},
        {"name": "EY", "base_url": "https://ey.taleo.net", "portal_id": "ey"},
        # Let's test with numeric portal ids
        {"name": "Starbucks (portal 1)", "base_url": "https://starbucks.taleo.net", "portal_id": "1"},
        {"name": "Starbucks (portal 2)", "base_url": "https://starbucks.taleo.net", "portal_id": "2"},
        {"name": "Starbucks (portal 10161)", "base_url": "https://starbucks.taleo.net", "portal_id": "10161"},
        {"name": "Deloitte (portal 1)", "base_url": "https://deloitte.taleo.net", "portal_id": "1"},
        {"name": "Deloitte (portal 2)", "base_url": "https://deloitte.taleo.net", "portal_id": "2"},
        {"name": "Deloitte (portal 10161)", "base_url": "https://deloitte.taleo.net", "portal_id": "10161"},
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [check_taleo_company(session, c["name"], c["base_url"], c["portal_id"]) for c in companies]
        results = await asyncio.gather(*tasks)
        for r in results:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
