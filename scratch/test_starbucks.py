import asyncio
import aiohttp

async def main():
    base_url = "https://starbucks.taleo.net"
    portal_id = "10120"
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
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            print("Status:", resp.status)
            if resp.status == 200:
                data = await resp.json()
                print("Total Count:", data.get("totalCount"))
                print("Jobs returned:", len(data.get("requisitionList", [])))
                if data.get("requisitionList"):
                    first = data.get("requisitionList")[0]
                    print("First Job Title:", first.get("column", [{}])[0].get("value"))
                    print("First Job Info:", first)
            else:
                print("Response:", await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
