import asyncio
from playwright.async_api import async_playwright
import json
from urllib.parse import quote, unquote

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        lat, lng = 28.6749, 77.2941
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([
            {"name": "user_position", "value": position, "domain": ".zeptonow.com", "path": "/"},
            {"name": "user_position", "value": position, "domain": ".zepto.com", "path": "/"}
        ])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        await asyncio.sleep(2)
        
        cookies = await context.cookies()
        serv = next((c for c in cookies if c["name"] == "serviceability"), None)
        if serv:
            data = json.loads(unquote(serv["value"]))
            print(json.dumps(data.get("storeDetailedInfo"), indent=2))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
