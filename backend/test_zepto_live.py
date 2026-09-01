import asyncio
import logging
from app.platforms.zepto import ZeptoClient

logging.basicConfig(level=logging.INFO)

async def test():
    client = ZeptoClient()
    # HSR Layout coords
    lat, lng = 12.9141, 77.6411
    
    # We need a valid Zepto product ID.
    # Let's use a sample one. Or just do resolve_store.
    print("Resolving store...")
    res = await client.resolve_store(lat, lng)
    print("Store Resolution:", res)
    
    if res.serviceable and res.store_id:
        print("Product at store...")
        # dummy product id
        prod = await client.product_at_store("502699f1-3315-464a-9c71-066bc332e293", res.store_id)
        print("Product:", prod)

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
