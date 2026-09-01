import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    async with async_playwright() as p:
        # Launch headed to see if that bypasses some bot detection if it relies on headless=True
        # Or at least headless=False might have different behavior, but we are in a headless environment.
        # We'll use a realistic user agent and standard viewport.
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        print("Navigating to Zepto...")
        
        try:
            resp = await page.goto("https://www.zeptonow.com/", wait_until="networkidle", timeout=20000)
            print(f"Status: {resp.status}")
            
            # Wait a few seconds to see if WAF challenge solves itself
            await page.wait_for_timeout(5000)
            
            content = await page.content()
            if "challenge" in content.lower():
                print("WAF Challenge detected in body after waiting.")
            elif "captcha" in content.lower():
                print("Captcha detected in body after waiting.")
            else:
                print("Page loaded successfully.")
                print(f"Title: {await page.title()}")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_playwright())
