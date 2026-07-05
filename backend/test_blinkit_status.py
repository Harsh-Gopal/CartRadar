import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-IN",
            viewport={"width": 1280, "height": 800}
        )
        page = await ctx.new_page()

        lat, lng = 30.7379, 76.6551 
        async def handle_route(route):
            try:
                headers = route.request.headers
                headers["lat"] = str(lat)
                headers["lon"] = str(lng)
                await route.continue_(headers=headers)
            except:
                await route.continue_()

        await page.route("**/v1/**", handle_route)
        
        async def on_response(response):
            if "484783" in response.url:
                print("STATUS:", response.status)
                if response.status != 200:
                    print("BODY:", await response.text())
            
        page.on("response", on_response)
        
        await page.goto("https://blinkit.com/prn/product/prid/484783", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(main())
