import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://www.flipkart.com/realme-buds-wireless-5-50db-anc-360-degree-spatial-audio-ip55-38hrs-playback-bluetooth/p/itm98edfd0118e5a?pid=ACCH6SR8QPWRQEGB&lid=LSTACCH6SR8QPWRQEGBGEBQQD&marketplace=HYPERLOCAL&pageUID=1788207169816"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Listen to all API responses
        responses = []
        page.on("response", lambda response: responses.append(response))

        print("Navigating...")
        await page.goto(url, wait_until="networkidle")
        
        # Look at the responses
        for res in responses:
            if "api" in res.url or "graphql" in res.url or "1/action" in res.url or "4/page" in res.url:
                try:
                    data = await res.json()
                    print(f"JSON Response from {res.url[:80]}...")
                    with open(f"response_{res.url.split('/')[-1].split('?')[0]}.json", "w") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    pass

        await browser.close()

asyncio.run(main())
