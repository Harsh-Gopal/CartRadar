import asyncio
import httpx
import json

URL_HOME = "https://www.zeptonow.com/"
URL_BFF = "https://bff-gateway.zepto.com/product-assortment-service/api/v2/product-detail?storeId=0059ff6a-7eb0-477a-a7f5-69256f2c444b&productVariantId=502699f1-3315-464a-9c71-066bc332e293"
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
HEADERS_API = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "platform": "WEB",
    "tenant": "ZEPTO",
    "app_version": "16.2.11"
}

async def test_methods():
    async with httpx.AsyncClient() as client:
        print("--- Method 1: Direct GET to zeptonow.com ---")
        try:
            resp = await client.get(URL_HOME, headers=HEADERS_WEB, timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Headers: {resp.headers}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- Method 2: Direct GET to bff-gateway.zepto.com ---")
        try:
            resp = await client.get(URL_BFF, headers=HEADERS_API, timeout=10)
            print(f"Status: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- Method 3: Mobile User-Agent to BFF ---")
        headers_mobile = HEADERS_API.copy()
        headers_mobile["User-Agent"] = "Zepto/8.5.1 (iPhone; iOS 17.3; Scale/3.00)"
        headers_mobile["platform"] = "IOS"
        try:
            resp = await client.get(URL_BFF, headers=headers_mobile, timeout=10)
            print(f"Status: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")
            
        print("\n--- Method 4: Test static Next.js asset ---")
        try:
            # Let's try fetching the build ID or something to see if CloudFront blocks everything
            resp = await client.get("https://www.zeptonow.com/manifest.json", headers=HEADERS_WEB, timeout=10)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(resp.text[:100])
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_methods())
