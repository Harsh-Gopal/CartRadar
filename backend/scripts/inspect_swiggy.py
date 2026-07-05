import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to Swiggy API...")
        
        # Swiggy uses dapi/misc/place-autocomplete
        response = await page.goto("https://www.swiggy.com/dapi/misc/place-autocomplete?input=560001&types=")
        await page.wait_for_timeout(3000)
        
        text = await response.text()
        print("Response:", text[:200])

        cookies = await context.cookies()
        print("\nCookies:", [(c["name"], c["value"][:20]) for c in cookies])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
