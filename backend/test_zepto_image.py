import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE
import sys
import os
import json

async def main():
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    store_id = "7e5a1821-59ed-4d8a-8431-a3705afb22d2"
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(12.9121, 77.6446)
        api_resp = await session.context.request.get(
            f"{BFF_BASE}/product-assortment-service/api/v2/product-detail?storeId={store_id}&productVariantId={pvid}",
            headers={
                "platform": "WEB",
                "tenant": "ZEPTO",
                "app_version": "16.2.11",
                "storeId": store_id
            },
            timeout=10000
        )
        data = await api_resp.json()
        product = data.get("product") or {}
        store_products = product.get("storeProducts") or []
        variant = {}
        if store_products:
            variant = store_products[0].get("productVariant") or {}
        
        images = variant.get('images') or product.get('images') or []
        print(f"Images array: {images}")
        if images:
            print(f"First image path: {images[0].get('path')}")
            
        print(json.dumps(data, indent=2)[:500])

if __name__ == "__main__":
    asyncio.run(main())
