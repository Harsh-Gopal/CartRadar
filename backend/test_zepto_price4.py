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
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    text = await response.text()
                    import json
                    if "sellingPrice" in text:
                        print(f"\n<< {response.status} {response.url}")
                        try:
                            data = json.loads(text)
                            def find_price(obj):
                                if isinstance(obj, dict):
                                    if "sellingPrice" in obj or "discountedSellingPrice" in obj:
                                        print(f"Product: {obj.get('product', {}).get('name', 'Unknown')}")
                                        for k, v in obj.items():
                                            if "price" in k.lower() or "mrp" in k.lower():
                                                print(f"  {k}: {v}")
                                    for v in obj.values():
                                        find_price(v)
                                elif isinstance(obj, list):
                                    for v in obj:
                                        find_price(v)
                            find_price(data)
                        except:
                            # Might be RSC payload (text but not pure json)
                            import re
                            matches = re.findall(r'"sellingPrice":(\d+)', text)
                            if matches:
                                print(f"Found sellingPrice matches: {matches}")
                                
                except Exception as e:
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
        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
