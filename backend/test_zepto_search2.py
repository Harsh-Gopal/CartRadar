import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_response(response):
            if "search" in response.url or "product-detail" in response.url:
                try:
                    text = await response.text()
                    import json
                    if "Colgate" in text:
                        print(f"\n<< {response.status} {response.url}")
                        print(f"Body: {text[:1000]}")
                except:
                    pass
                    
        page.on("response", handle_response)
        
        print("Navigating to Zepto...")
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
        
        print("Searching for 'milk'...")
        # Since the search API failed earlier, let's just type into the UI!
        # First we might need to close any modals or just click the search bar
        try:
            await page.click("text=Search", timeout=5000)
            await page.fill("input[placeholder*='Search']", "milk", timeout=5000)
            await page.wait_for_timeout(3000)
            # click the first product
            await page.click("a[href*='/pn/']", timeout=5000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"UI interaction failed: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
