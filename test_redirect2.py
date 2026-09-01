import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.flipkart.com/p/itm?pid=ACCH6SR8QPWRQEGB&marketplace=FLIPKART", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        content = await page.content()
        if "realme Buds" in content:
            print("Product found!")
        else:
            print("Product NOT found!")
        await browser.close()
asyncio.run(main())
