import asyncio
from playwright.async_api import async_playwright
import json
from urllib.parse import quote

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        lat, lng = 28.6749, 77.2941
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([
            {"name": "user_position", "value": position, "domain": ".zeptonow.com", "path": "/"},
            {"name": "user_position", "value": position, "domain": ".zepto.com", "path": "/"}
        ])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Get local storage
        ls = await page.evaluate("() => JSON.stringify(localStorage)")
        print(f"LocalStorage keys: {list(json.loads(ls).keys())}")
        
        # Print anything that looks like it has store coordinates
        for k, v in json.loads(ls).items():
            if "store" in k.lower() or "service" in k.lower() or "address" in k.lower() or "location" in k.lower() or "cache" in k.lower() or "redux" in k.lower() or "state" in k.lower():
                print(f"\n[LocalStorage] {k}")
                print(f"{v[:500]}...")
                
        # Also check window object for redux state or NEXT_DATA
        next_data = await page.evaluate("() => window.__NEXT_DATA__ || {}")
        if next_data:
            print(f"\n[NEXT_DATA] found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
