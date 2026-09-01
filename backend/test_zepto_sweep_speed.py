import asyncio
import json
import time
from urllib.parse import quote, unquote
from playwright.async_api import async_playwright

async def test_speed():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        print("Solving WAF...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        locations = [
            (12.9141, 77.6411),
            (12.9151, 77.6421),
            (12.9161, 77.6431),
            (12.9171, 77.6441),
            (12.9181, 77.6451),
        ]
        
        start = time.time()
        for lat, lng in locations:
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
            
            # Using domcontentloaded instead of networkidle is much faster!
            t0 = time.time()
            await page.goto("https://www.zeptonow.com/", wait_until="domcontentloaded")
            # Wait just a tiny bit for the server to set the cookie
            await asyncio.sleep(0.5) 
            
            cookies = await context.cookies()
            serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
            store_id = None
            if serviceability:
                data = json.loads(unquote(serviceability["value"]))
                store_id = data.get('primaryStore', {}).get('storeId')
                
            print(f"Point {lat},{lng} took {time.time()-t0:.2f}s -> StoreID: {store_id}")
            
        print(f"Total time for 5 points: {time.time()-start:.2f}s")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_speed())
