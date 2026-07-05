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

        print("Navigating to BigBasket...")
        
        async def handle_response(response):
            if ("/pd/" in response.url or "/product/" in response.url or "/custompage/" in response.url or "/api/" in response.url or "places/" in response.url or "location" in response.url):
                print(f"API URL: {response.url} ({response.status})")
                try:
                    js = await response.json()
                    print(json.dumps(js)[:300] + "...")
                except Exception as e:
                    pass

        page.on("response", handle_response)
        
        # We need a product URL, let's search for "tata salt"
        await page.goto("https://www.bigbasket.com/pd/241602/tata-salt-iodised-1-kg-pouch/", wait_until="networkidle")
        
        await asyncio.sleep(8)
        
        cookies = await context.cookies()
        print("\nCookies:")
        for cookie in cookies:
            if cookie['name'].startswith("_bb"):
                print(f"- {cookie['name']}: {cookie['value'][:40]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
