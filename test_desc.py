import asyncio
import aiohttp
import html as html_module
from bs4 import BeautifulSoup

async def test():
    async with aiohttp.ClientSession() as session:
        url = "https://boards-api.greenhouse.io/v1/boards/figma/jobs/5839202004"
        async with session.get(url) as resp:
            data = await resp.json()
            raw_content = data.get("content", "")
            
            # Step 1: unescape
            decoded = raw_content
            for _ in range(3):
                if not any(e in decoded for e in ("&lt;", "&gt;", "&amp;", "&quot;", "&#")):
                    break
                decoded = html_module.unescape(decoded)
            
            # Step 2: BeautifulSoup
            soup = BeautifulSoup(decoded, "html.parser")
            text = soup.get_text("\n", strip=False)
            
            print(f"Final text length: {len(text)}")
            print(f"Last 300 chars:\n{text[-300:]}")

asyncio.run(test())