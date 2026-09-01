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
        
        cookies = await context.cookies()
        serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
        if not serviceability:
            print("No serviceability cookie!")
            return
            
        data = json.loads(unquote(serviceability["value"]))
        store_id = data.get("primaryStore", {}).get("storeId")
        print(f"Primary Store ID: {store_id}")
        
        pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70" # Amul milk
        
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
            sp = prod_data.get("product", {}).get("storeProducts", [{}])[0]
            print("\nPrice fields:")
            for k, v in sp.items():
                if "price" in k.lower() or "mrp" in k.lower():
                    print(f"  {k}: {v}")
        else:
            print(f"API failed: {resp.status}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
