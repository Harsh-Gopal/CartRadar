import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        await page.goto("https://www.flipkart.com/product/p/itme?pid=ACCH6SR8QPWRQEGB&marketplace=FLIPKART", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        content = await page.content()
        if "realme Buds" in content:
            print("Product found!")
        else:
            print("Product NOT found!")
        await browser.close()
asyncio.run(main())
