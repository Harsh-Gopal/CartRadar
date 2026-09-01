import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        async def handle_response(response):
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    text = await response.text()
                    if "7e5a1821-59ed-4d8a-8431-a3705afb22d2" in text or "latitude" in text or "longitude" in text:
                        print(f"\n<< {response.status} {response.url}")
                        print(f"Body snippet: {text[:500]}")
                except Exception:
                    pass
                    
        page.on("response", handle_response)
        
        print("Navigating to Zepto (HSR Layout)...")
        import json
        from urllib.parse import quote
        lat, lng = 12.9141, 77.6411 # HSR Layout
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
