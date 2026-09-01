import asyncio
from playwright.async_api import async_playwright
import json

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_response(response):
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    text = await response.text()
                    # We are looking for something that exposes multiple stores and their real coordinates
                    if "latitude" in text.lower() or "lat" in text.lower():
                        print(f"\n[JSON] {response.url}")
                        # Print keys or first few hundred chars
                        data = json.loads(text)
                        
                        def find_stores(d):
                            if isinstance(d, dict):
                                if "storeId" in d and ("latitude" in d or "lat" in d):
                                    print(f"Found store with coords: {d.get('storeId')}")
                                for k, v in d.items():
                                    find_stores(v)
                            elif isinstance(d, list):
                                for item in d:
                                    find_stores(item)
                                    
                        find_stores(data)
                        print(f"Data snippet: {text[:200]}")
                except Exception:
                    pass

        page.on("response", handle_response)
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        # Click the location picker
        try:
            await page.click("button[data-testid='location-selector']", timeout=3000)
            await page.wait_for_timeout(1000)
            # Type Shahdara
            await page.fill("input[placeholder='Search a new address']", "Delhi Shahdara", timeout=3000)
            await page.wait_for_timeout(3000)
            # Click the first suggestion
            await page.click("div[data-testid='location-suggestion-item']", timeout=3000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"UI interaction failed: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
