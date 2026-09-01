import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.flipkart.com/realme-buds-wireless-5-50db-anc-360-degree-spatial-audio-ip55-38hrs-playback-bluetooth/p/itm98edfd0118e5a?pid=ACCH6SR8QPWRQEGB&lid=LSTACCH6SR8QPWRQEGBGEBQQD&marketplace=HYPERLOCAL&pageUID=1788207169816"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            geolocation={"longitude": 77.5946, "latitude": 12.9716},
            permissions=["geolocation"]
        )
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        locators = await page.locator("text=/Use my current location/i").all()
        if locators:
            await locators[0].click()
            await page.wait_for_timeout(5000)
            
        cookies = await context.cookies()
        import json
        with open("flipkart_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)
            
        await browser.close()

asyncio.run(main())
