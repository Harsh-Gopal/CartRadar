import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE
import json
from urllib.parse import quote
import httpx

async def main():
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6139, 77.2090)
        
        cookies = await session.context.cookies()
        waf_cookies = {c["name"]: c["value"] for c in cookies if c["name"].startswith("datadome")}
        
        # Test Bangalore location
        lat, lng = 12.9121, 77.6446
        store_id = "7e5a1821-59ed-4d8a-8431-a3705afb22d2"
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        req_cookies = waf_cookies.copy()
        req_cookies["user_position"] = position
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BFF_BASE}/product-assortment-service/api/v2/product-detail?storeId={store_id}&productVariantId={pvid}",
                headers={
                    "platform": "WEB",
                    "tenant": "ZEPTO",
                    "storeId": store_id,
                    "app_version": "16.2.11"
                },
                cookies=req_cookies
            )
            print("Status code:", resp.status_code)
            print("Text:", resp.text[:500])

if __name__ == "__main__":
    asyncio.run(main())
