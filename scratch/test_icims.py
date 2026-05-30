import asyncio
import aiohttp

async def test_sitemap(session, name, base_url):
    url = f"{base_url.rstrip('/')}/sitemap.xml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": base_url,
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            text = await resp.text()
            print(f"{name}: status={resp.status}, content_type={resp.headers.get('Content-Type')}")
            if resp.status == 200:
                print(f"  -> SUCCESS! Text preview: {text[:200]}")
            else:
                print(f"  -> Failed. Text preview: {text[:200]}")
    except Exception as e:
        print(f"{name}: error: {e}")

async def main():
    companies = [
        {"name": "FedEx", "base_url": "https://careers-fedex.icims.com"},
        {"name": "Ford", "base_url": "https://careers-ford.icims.com"},
        {"name": "General Motors", "base_url": "https://careers-gm.icims.com"},
        {"name": "Northrop Grumman", "base_url": "https://careers-northropgrumman.icims.com"},
        {"name": "Lockheed Martin", "base_url": "https://careers-lockheedmartin.icims.com"},
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [test_sitemap(session, c["name"], c["base_url"]) for c in companies]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
