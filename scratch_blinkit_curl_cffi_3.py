import asyncio
from curl_cffi.requests import AsyncSession
import json

async def main():
    async with AsyncSession(impersonate="chrome110") as s:
        product_id = "11149"
        lat, lng = "30.743", "76.657"
        urls = [
            f"https://blinkit.com/api/v1/layout/product/{product_id}",
            f"https://blinkit.com/api/v2/layout/product/{product_id}",
            f"https://blinkit.com/api/v3/layout/product/{product_id}",
            f"https://blinkit.com/api/v4/layout/product/{product_id}",
            f"https://blinkit.com/api/v1/layout/product/{product_id}/",
        ]
        
        headers = {
            "lat": lat,
            "lon": lng,
            "app_client": "consumer_web"
        }
        
        for url in urls:
            resp = await s.get(url, headers=headers)
            print("URL:", url, "Status:", resp.status_code)
            if resp.status_code == 200:
                print("BODY:", resp.text[:100])

if __name__ == "__main__":
    asyncio.run(main())
