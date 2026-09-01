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
        print("Page loaded. Title:", await page.title())
        
        # Check for CAPTCHA
        content = await page.content()
        if "reCAPTCHA" in content or "Are you a human?" in content:
            print("Blocked by CAPTCHA")
            await browser.close()
            return

        # Check if we can input a pincode
        # Wait a bit
        await page.wait_for_timeout(2000)
        
        # Take a screenshot
        await page.screenshot(path="flipkart_test.png")
        print("Screenshot saved to flipkart_test.png")
        
        await browser.close()

asyncio.run(main())
