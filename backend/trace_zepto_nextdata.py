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
        await asyncio.sleep(2)
        
        # Get next data
        next_data = await page.evaluate("() => window.__NEXT_DATA__ || {}")
        if next_data:
            out = json.dumps(next_data)
            # Find any lat/lng or stores
            print(f"Total NEXT_DATA size: {len(out)}")
            if "latitude" in out.lower() or "lat" in out.lower():
                print("Found lat/lng in NEXT_DATA")
                
            # dump to file for inspection
            with open("zepto_next_data.json", "w") as f:
                f.write(out)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
