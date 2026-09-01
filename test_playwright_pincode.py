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

        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded")
        
        # Wait a bit for the bottom sheet
        await page.wait_for_timeout(2000)
        
        # Try to find pincode input
        input_sel = "input[placeholder*='pincode'], input[placeholder*='Pincode']"
        inputs = await page.locator(input_sel).all()
        print(f"Found {len(inputs)} pincode inputs")
        
        if len(inputs) == 0:
            # Maybe we need to click a delivery button first?
            print("Looking for delivery button...")
            deliver_btns = await page.locator("text=/Deliver to|Enter pincode/i").all()
            if deliver_btns:
                await deliver_btns[0].click()
                await page.wait_for_timeout(1000)
                inputs = await page.locator(input_sel).all()
                print(f"Found {len(inputs)} pincode inputs after click")

        if inputs:
            await inputs[0].fill("560001") # Sample Bangalore Pincode
            await inputs[0].press("Enter")
            print("Filled pincode 560001 and pressed enter")
            
            await page.wait_for_timeout(3000)
            await page.screenshot(path="flipkart_pincode.png")
            print("Saved screenshot to flipkart_pincode.png")
            
        await browser.close()

asyncio.run(main())
