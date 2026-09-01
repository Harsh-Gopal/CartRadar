import asyncio
from playwright.async_api import async_playwright

async def main():
    product_id = "ACCH6SR8QPWRQEGB"
    lat, lng = 12.9716, 77.5946
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            geolocation={"longitude": lng, "latitude": lat},
            permissions=["geolocation"]
        )
        page = await context.new_page()
        url = f"https://www.flipkart.com/product/p/itme?pid={product_id}&marketplace=HYPERLOCAL"
        
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        
        locators = await page.locator("text=/Use my current location/i").all()
        if locators:
            print("Clicking Use my current location...")
            await locators[0].click(timeout=5000)
            await page.wait_for_timeout(4000)
            
        print("Final URL:", page.url)
        content = await page.content()
        print("Page length:", len(content))
        await browser.close()
        
asyncio.run(main())
