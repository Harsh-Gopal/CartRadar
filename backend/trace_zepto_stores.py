import asyncio
from playwright.async_api import async_playwright
import json
from urllib.parse import quote, unquote

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_response(response):
            url = response.url
            if "zepto" in url and ("store" in url or "service" in url or "location" in url or "address" in url or "layout" in url):
                try:
                    text = await response.text()
                    if "storeId" in text:
                        print(f"\n[GET] {url}")
                        print(f"Response: {text[:500]}...")
                except Exception:
                    pass

        page.on("response", handle_response)
        
        # We will use Shahdara coordinates: 28.6749, 77.2941
        lat, lng = 28.6749, 77.2941
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        print("Setting user_position cookie for Shahdara and navigating to Zepto...")
        await context.add_cookies([
            {"name": "user_position", "value": position, "domain": ".zeptonow.com", "path": "/"},
            {"name": "user_position", "value": position, "domain": ".zepto.com", "path": "/"}
        ])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Let's also check the actual serviceability cookie to see what's in it.
        cookies = await context.cookies()
        serv = next((c for c in cookies if c["name"] == "serviceability"), None)
        if serv:
            data = json.loads(unquote(serv["value"]))
            print(f"\n[COOKIE] serviceability stores: {list(data.get('storesData', {}).keys())}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
