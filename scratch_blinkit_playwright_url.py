import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        async def on_response(response):
            if "/v1/" in response.url:
                print(f"URL: {response.url}")
        
        page.on("response", on_response)
        await page.goto("https://blinkit.com/prn/product/prid/11149", wait_until="networkidle")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
