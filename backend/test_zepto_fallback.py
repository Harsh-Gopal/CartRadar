import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession

async def main():
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    home_lat, home_lng = 30.7333, 76.7794 # Chandigarh
    
    async with ZeptoPlaywrightSession() as session:
        # Probe Chandigarh
        res = await session.probe_location(home_lat, home_lng)
        store_id = res.get("store_id")
        print("Home store:", store_id)
        
        # Check product at home store
        if store_id:
            prod_home = await session.check_product(store_id, pvid)
            print("Home product name:", prod_home.name)
        
        # Check product at HSR Layout (fallback)
        fallback_store = "7e5a1821-59ed-4d8a-8431-a3705afb22d2"
        prod_fallback = await session.check_product(fallback_store, pvid)
        print("Fallback product name:", prod_fallback.name)
        print("Fallback product image:", prod_fallback.image_url)

if __name__ == "__main__":
    asyncio.run(main())
