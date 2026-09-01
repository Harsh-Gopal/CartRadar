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
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        import json
        from urllib.parse import quote, unquote
        # Kharar coordinates
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
        
        await page.goto("https://www.zeptonow.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        cookies = await context.cookies()
        serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
        if serviceability:
            raw = unquote(serviceability["value"])
            print(f"Serviceability cookie:\n{raw}")
            data = json.loads(raw)
            print(f"Primary Store: {data.get('primaryStore')}")
            print(f"Store Info: {data.get('storeDetailedInfo')}")
            
            store_id = data.get('primaryStore', {}).get('storeId')
            
            if store_id:
                # Test the product detail API for price
                # We need a product ID. Let's use Colgate Visible White
                pvid = "502699f1-3315-464a-9c71-066bc332e293" # Test ID from earlier
                print(f"\nFetching product {pvid} for store {store_id}...")
                
                resp = await context.request.get(
                    f"https://bff-gateway.zepto.com/product-assortment-service/api/v2/product-detail?storeId={store_id}&productVariantId={pvid}",
                    headers={
                        "platform": "WEB",
                        "tenant": "ZEPTO",
                        "app_version": "16.2.11",
                        "storeId": store_id
                    }
                )
                if resp.ok:
                    prod_data = await resp.json()
                    print(f"Product API Response:\n{json.dumps(prod_data, indent=2)}")
                else:
                    print(f"Product API failed: {resp.status} {await resp.text()}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
