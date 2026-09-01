import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        import json
        from urllib.parse import quote, unquote
        lat, lng = 30.7415, 76.6521
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
        
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        cookies = await context.cookies()
        serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
        data = json.loads(unquote(serviceability["value"]))
        store_id = data.get("primaryStore", {}).get("storeId")
        
        # Search for "milk"
        resp = await context.request.get(
            f"https://bff-gateway.zepto.com/api/v3/search/search-bar?query=milk&pageNumber=1&mode=AUTOSUGGEST&storeId={store_id}",
            headers={
                "platform": "WEB",
                "tenant": "ZEPTO",
                "app_version": "16.2.11",
                "storeId": store_id
            }
        )
        if resp.ok:
            search_data = await resp.json()
            products = search_data.get("layout", [])
            for p in products:
                if p.get("widgetId") == "PRODUCT_GRID":
                    items = p.get("widgetData", {}).get("items", [])
                    if items:
                        item = items[0]
                        pvid = item.get("productVariant", {}).get("id")
                        print(f"Found product: {item.get('product', {}).get('name')}")
                        print(f"PVID: {pvid}")
                        
                        sp = item.get("storeProducts", [{}])[0]
                        print("\nPrice fields:")
                        for k, v in sp.items():
                            if "price" in k.lower() or "mrp" in k.lower():
                                print(f"  {k}: {v}")
                        break
        else:
            print(f"API failed: {resp.status} {await resp.text()}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
