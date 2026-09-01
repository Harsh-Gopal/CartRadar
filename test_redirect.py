import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.flipkart.com/p/itm?pid=ACCH6SR8QPWRQEGB&marketplace=FLIPKART")
        print(page.url)
        await browser.close()
asyncio.run(main())
