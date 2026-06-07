import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://careers-hyland.icims.com/jobs/search?pr=0"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"))
            page = await context.new_page()
            # try a lighter wait first
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            try:
                await page.wait_for_selector('.iCIMS_JobsTable .row', timeout=15000)
                print('selector found')
            except Exception as se:
                print('selector not found or timed out:', se)
            title = await page.title()
            print('title=', title)
            content = await page.content()
            print('len content=', len(content))
            await browser.close()
    except Exception as e:
        print('error:', e)

if __name__ == '__main__':
    asyncio.run(main())
