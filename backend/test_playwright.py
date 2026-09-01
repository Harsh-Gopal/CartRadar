import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        print("Navigating to Zepto...")
        resp = await page.goto("https://www.zeptonow.com/")
        print("Status:", resp.status)
        
        print("Cookies:", await context.cookies())
        content = await page.content()
        if "challenge" in content.lower():
            print("WAF Challenge detected in body.")
        elif "captcha" in content.lower():
            print("Captcha detected in body.")
        else:
            print("Page loaded successfully.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
