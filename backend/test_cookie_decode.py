import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print("Navigating to Zepto...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        import json
        from urllib.parse import quote, unquote
        lat, lng = 12.9141, 77.6411 # HSR Layout
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zepto.com",
            "path": "/"
        }, {
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        await page.goto("https://www.zeptonow.com/", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        cookies = await context.cookies()
        serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
        if serviceability:
            raw = unquote(serviceability["value"])
            print(f"Serviceability cookie:\n{raw}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
