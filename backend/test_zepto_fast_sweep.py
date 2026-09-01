import asyncio
import httpx
from playwright.async_api import async_playwright
import json
from urllib.parse import quote, unquote

async def run_trace():
    lat, lng = 28.6749, 77.2941
    position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.goto("https://www.zeptonow.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        cookies = await context.cookies()
        waf_cookies = {c["name"]: c["value"] for c in cookies if c["name"] not in ["serviceability", "storeId", "user_position", "selectedAddress", "addressId"]}
        await browser.close()
        
    async with httpx.AsyncClient(follow_redirects=True) as client:
        client.cookies.update(waf_cookies)
        client.cookies.set("user_position", position, domain=".zeptonow.com", path="/")
        client.cookies.set("user_position", position, domain=".zepto.com", path="/")
        
        resp = await client.request(
            "HEAD",
            "https://www.zeptonow.com/",
            headers={
                "Accept": "text/html",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        )
        if resp.status_code == 200:
            for name, value in resp.cookies.items():
                if name == "serviceability":
                    data = json.loads(unquote(value))
                    print(json.dumps(data, indent=2))
            
if __name__ == "__main__":
    asyncio.run(run_trace())
