import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE

async def main():
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    
    async with ZeptoPlaywrightSession() as session:
        # We start with Delhi location
        res = await session.probe_location(28.6139, 77.2090)
        delhi_store = res.get("store_id")
        print("Delhi store:", delhi_store)
        
        if delhi_store:
            prod_delhi = await session.check_product(delhi_store, pvid)
            print("Delhi price (API):", prod_delhi.price)
        
        # Now query Bangalore store using same context
        blr_store = "7e5a1821-59ed-4d8a-8431-a3705afb22d2"
        prod_blr = await session.check_product(blr_store, pvid)
        print("BLR price (API):", prod_blr.price)
        
if __name__ == "__main__":
    asyncio.run(main())
