import asyncio
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
                if "/v1/" in route.request.url:
                    headers = route.request.headers
                    headers["lat"] = str(lat)
                    headers["lon"] = str(lng)
                    await route.continue_(headers=headers)
                else:
                    await route.continue_()
            except Exception as e:
                print(f"Exception: {e}")
                await route.continue_()

        await page.route("**/*", handle_route)
        
        async def on_request(request):
            print("REQ:", request.url)
            
        page.on("request", on_request)
        
        await page.goto("https://blinkit.com/prn/product/prid/484783", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(main())
