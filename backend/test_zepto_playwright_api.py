import asyncio
import json
from urllib.parse import quote
from playwright.async_api import async_playwright

async def test_playwright_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        # HSR Layout coordinates
        lat, lng = 12.9141, 77.6411
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
        print("Navigating to Zepto homepage to solve WAF and get serviceability cookie...")
        
        resp = await page.goto("https://www.zeptonow.com/", wait_until="networkidle", timeout=20000)
        
        # Wait for the serviceability cookie to be set
        await page.wait_for_timeout(3000)
        
        cookies = await context.cookies()
        serviceability_cookie = next((c for c in cookies if c["name"] == "serviceability"), None)
        
        if serviceability_cookie:
            print("Successfully got serviceability cookie!")
            print(f"Cookie value: {serviceability_cookie['value'][:100]}...")
            
            # Now let's try to get product details using page.request
            # Product variant: 502699f1-3315-464a-9c71-066bc332e293
            
            # Extract storeId from the cookie
            from urllib.parse import unquote
            data = json.loads(unquote(serviceability_cookie["value"]))
            primary = data.get("primaryStore") or {}
            store_id = primary.get("storeId")
            
            print(f"Store ID extracted: {store_id}")
            
            if store_id:
                print("Fetching product details via Playwright context...")
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
            print(f"Current cookies: {[c['name'] for c in cookies]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_playwright_api())
