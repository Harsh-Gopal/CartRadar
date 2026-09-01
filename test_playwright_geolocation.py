import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://www.flipkart.com/realme-buds-wireless-5-50db-anc-360-degree-spatial-audio-ip55-38hrs-playback-bluetooth/p/itm98edfd0118e5a?pid=ACCH6SR8QPWRQEGB&lid=LSTACCH6SR8QPWRQEGBGEBQQD&marketplace=HYPERLOCAL&pageUID=1788207169816"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Grant geolocation permissions and set location
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            geolocation={"longitude": 77.5946, "latitude": 12.9716}, # Bangalore
            permissions=["geolocation"]
        )
        page = await context.new_page()

        # Listen to all API responses
        responses = []
        page.on("response", lambda response: responses.append(response))

        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded")
        
        await page.wait_for_timeout(3000)
        
        # Click "Use my current location"
        locators = await page.locator("text=/Use my current location/i").all()
        if locators:
            print("Clicking Use my current location...")
            await locators[0].click()
            await page.wait_for_timeout(5000)
        else:
            print("Could not find Use my current location button")
            
        await page.screenshot(path="flipkart_geolocation.png")
        print("Saved screenshot to flipkart_geolocation.png")
        
        # Let's save responses
        for res in responses:
            if "api" in res.url or "graphql" in res.url or "1/action" in res.url or "4/page" in res.url:
                try:
                    data = await res.json()
                    name = res.url.split('/')[-1].split('?')[0]
                    if "fetch" in name:
                        with open(f"response_geo_{name}.json", "w") as f:
                            json.dump(data, f, indent=2)
                except Exception:
                    pass

        await browser.close()

asyncio.run(main())
