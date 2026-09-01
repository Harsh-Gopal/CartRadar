import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # We need to capture response bodies, which we can do by attaching an event listener.
        async def handle_response(response):
            if "lms/api/v2/get_page" in response.url:
                print(f"<< {response.status} {response.url}")
                try:
                    text = await response.text()
                    print(f"Body: {text[:500]}...")
                except Exception as e:
                    print(f"Failed to get body: {e}")
                    
        page.on("response", handle_response)
        
        print("Navigating to Zepto...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        print("\nSetting Kharar location and navigating...")
        import json
        from urllib.parse import quote
        lat, lng = 30.7415, 76.6521
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
