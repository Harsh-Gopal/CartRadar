import asyncio
from app.platforms.zepto.client import ZeptoClient
from app.platforms.zepto.search import run_zepto_search
from app.store_cache import StoreCache

async def main():
    client = ZeptoClient()
    cache = StoreCache(":memory:")
    
    # Coca-Cola PET Cola
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    lat, lng = 28.6811, 77.2917 # Shahdara
    
    print("Running Zepto search...")
    async for result in run_zepto_search(client, pvid, lat, lng, 3.0, cache):
        if result["type"] == "home_result":
            print(f"HOME RESULT: Serviceable? {result['serviceable']}, Store Name: {result.get('store_name')}")
            
        if result["type"] == "store_result":
            store = result["store"]
            status = result["status"]
            verified = result.get("verified")
            price = result.get("price")
            print(f"Store: {store['name']} ({store['id']})")
            print(f"  Verified Serving Store: {verified}")
            print(f"  Status: {status}")
            print(f"  Price: {price}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
