import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Log all responses
        page.on("response", lambda response: print(f"<< {response.status} {response.url}"))
        
        print("Navigating to Zepto...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        print("\nCookies before location change:")
        cookies = await context.cookies()
        for c in cookies:
            if c['name'] in ('user_position', 'serviceability'):
                print(f"  {c['name']}: {c['value'][:100]}...")
                
        # We simulate what the frontend does when changing location:
        # Actually, let's just observe what happens if we navigate to a new location.
        print("\nSetting Kharar location and navigating...")
        import json
        from urllib.parse import quote
        lat, lng = 30.7415, 76.6521
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        print("\nCookies after location change:")
        cookies = await context.cookies()
        for c in cookies:
            if c['name'] in ('user_position', 'serviceability'):
                print(f"  {c['name']}: {c['value'][:100]}...")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
