import asyncio
import json
from urllib.parse import quote
from playwright.async_api import async_playwright

async def test_playwright_kharar():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
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

        page = await context.new_page()
        print("Navigating to Zepto homepage to solve WAF for Kharar...")
        
        resp = await page.goto("https://www.zeptonow.com/", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)
        
        cookies = await context.cookies()
        serviceability_cookie = next((c for c in cookies if c["name"] == "serviceability"), None)
        
        if serviceability_cookie:
            print("Successfully got serviceability cookie!")
            from urllib.parse import unquote
            data = json.loads(unquote(serviceability_cookie["value"]))
            primary = data.get("primaryStore") or {}
            store_id = primary.get("storeId")
            
            print(f"Kharar Store ID extracted: {store_id}")
            
            if store_id:
                # Try getting a different product (Amul Milk or similar)
                # Let's search for milk using the correct search API endpoint if we knew it, 
                # or just use the same product.
                api_resp = await context.request.get(
                    f"https://bff-gateway.zepto.com/product-assortment-service/api/v2/product-detail?storeId={store_id}&productVariantId=502699f1-3315-464a-9c71-066bc332e293",
                    headers={
                        "platform": "WEB",
                        "tenant": "ZEPTO",
                        "app_version": "16.2.11",
                        "storeId": store_id
                    }
                )
                print(f"Product API Status: {api_resp.status}")
                if api_resp.status == 200:
                    product_data = await api_resp.json()
                    product_name = product_data.get("product", {}).get("name")
                    print(f"Successfully fetched product: {product_name}")
                else:
                    print(f"Product API failed: {await api_resp.text()}")
        else:
            print("Failed to get serviceability cookie.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_playwright_kharar())
