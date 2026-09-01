import asyncio
import httpx
from urllib.parse import quote, unquote
import json
from playwright.async_api import async_playwright

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
        
        # Test 1: Using request parameter
        resp1 = await client.request(
            "HEAD",
            "https://www.zeptonow.com/",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"},
            cookies={"user_position": position}
        )
        s1 = resp1.cookies.get("serviceability")
        d1 = json.loads(unquote(s1)) if s1 else {}
        print("Test 1 (request arg) primaryStore:", d1.get("primaryStore"))
        
        # Test 2: Using client cookie jar
        client.cookies.set("user_position", position, domain=".zeptonow.com", path="/")
        resp2 = await client.request(
            "HEAD",
            "https://www.zeptonow.com/",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
        )
        s2 = resp2.cookies.get("serviceability")
        d2 = json.loads(unquote(s2)) if s2 else {}
        print("Test 2 (client jar) primaryStore:", d2.get("primaryStore"))

if __name__ == "__main__":
    asyncio.run(run_trace())
