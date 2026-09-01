import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Navigating to Zepto...")
        import json
        from urllib.parse import quote, unquote
        lat, lng = 30.7415, 76.6521
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        html = await page.content()
        import re
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
        if match:
            data = json.loads(match.group(1))
            print("Found NEXT_DATA!")
            # Recursively search for any object with 'sellingPrice'
            def find_price(obj):
                if isinstance(obj, dict):
                    if "sellingPrice" in obj or "discountedSellingPrice" in obj:
                        print(f"Product: {obj.get('product', {}).get('name', 'Unknown')}")
                        for k in obj.keys():
                            if "price" in k.lower() or "mrp" in k.lower():
                                print(f"  {k}: {obj[k]}")
                    for v in obj.values():
                        find_price(v)
                elif isinstance(obj, list):
                    for v in obj:
                        find_price(v)
            find_price(data)
        else:
            print("NEXT_DATA not found.")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
