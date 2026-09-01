import asyncio
from app.platforms.flipkart import FlipkartMinutesClient
from app.store_cache import StoreCache
from app.search import run_search

async def test_cache_deduplication():
    # In-memory DB for StoreCache
    cache = StoreCache(":memory:")
    client = FlipkartMinutesClient()
    
    product_id = "TPSH3PYAHTQEGTGF"
    lat1 = 25.601
    lng1 = 85.070
    
    print("--- FIRST RUN ---")
    stores_found_1 = 0
    # First search, force=True to simulate fresh scan
    async for event in run_search(client, cache, product_id, lat1, lng1, 3.0, force=True):
        if event["type"] == "store_result":
            stores_found_1 += 1
            print(f"Store Result 1: {event['store']['id']} at {event['store']['lat']}, {event['store']['lng']}")
    
    print(f"Stores found first time: {stores_found_1}")
    
    print("--- SECOND RUN (slightly different coordinates) ---")
    lat2 = 25.602
    lng2 = 85.071
    stores_found_2 = 0
    # Second search, force=False (rely on cache). 
    # Actually wait, force=False will just sweep grid.
    # We want to see if the second scan merges into the SAME store_id.
    async for event in run_search(client, cache, product_id, lat2, lng2, 3.0, force=True):
        if event["type"] == "store_result":
            stores_found_2 += 1
            print(f"Store Result 2: {event['store']['id']} at {event['store']['lat']}, {event['store']['lng']}")
            
    print(f"Stores found second time: {stores_found_2}")
    
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(test_cache_deduplication())
