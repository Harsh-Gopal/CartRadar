import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_request(request):
            if "product-detail" in request.url:
                print(f"URL: {request.url}")
                print(f"Headers: {request.headers}")
                
        page.on("request", handle_request)
        
        import json
        from urllib.parse import quote
        lat, lng = 30.7415, 76.6521
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }, {
            "name": "user_position",
            "value": position,
            "domain": ".zepto.com",
            "path": "/"
        }])
        
        print("Navigating to Paper Boat Coffee...")
        await page.goto("https://www.zeptonow.com/pn/paper-boat-zero-sparkling-coffee-caffeinated-drink/pvid/0651ed45-7cf6-453b-ba37-c5169094481c", wait_until="networkidle")
        
        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
