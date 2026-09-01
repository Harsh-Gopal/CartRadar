import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # We need to capture response bodies for product-detail
        async def handle_response(response):
            if "product-detail" in response.url:
                try:
                    text = await response.text()
                    import json
                    print(f"\n<< {response.status} {response.url}")
                    # Parse and print only the price fields
                    data = json.loads(text)
                    sp = data.get("product", {}).get("storeProducts", [{}])[0]
                    print("Price fields in storeProducts:")
                    for k, v in sp.items():
                        if "price" in k.lower() or "mrp" in k.lower():
                            print(f"  {k}: {v}")
                except Exception as e:
                    print(f"Failed to get body: {e}")
                    
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
        
        # We'll directly navigate to a known product URL.
        # e.g., Amul Taaza Toned Milk
        product_url = "https://www.zeptonow.com/pn/amul-taaza-toned-milk/pvid/e6417757-5503-490f-90e0-c3d5ffcb3a70"
        print(f"Navigating to {product_url}")
        await page.goto(product_url, wait_until="networkidle")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
