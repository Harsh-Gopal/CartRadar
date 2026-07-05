import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.bigbasket.com/pd/10000148/")
        c = await page.content()
        print(len(c))
        if "Access Denied" in c:
            print("Access denied")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
