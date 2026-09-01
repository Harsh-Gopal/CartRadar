import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE
import json

async def main():
    pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70"
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6083, 77.2987)
        api_resp = await session.context.request.get(
            f"{BFF_BASE}/product-assortment-service/api/v2/product-detail?productVariantId={pvid}",
            headers={
                "platform": "WEB",
                "tenant": "ZEPTO",
                "app_version": "16.2.11"
            },
            timeout=10000
        )
        print("Status:", api_resp.status)
        data = await api_resp.json()
        print(json.dumps(data, indent=2)[:500])

if __name__ == "__main__":
    asyncio.run(main())
