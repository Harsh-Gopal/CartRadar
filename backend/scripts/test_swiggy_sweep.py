import asyncio
from app.platforms.swiggy import SwiggyClient
from app.store_cache import StoreCache
from app.search import run_search
from pathlib import Path

async def main():
    # Use memory cache for isolating this temp sweep
    cache = StoreCache(":memory:")
    client = SwiggyClient()
    
    # New Delhi coords from user's screenshot
    lat, lng = 28.6273928, 77.1716954
    product_id = "PSHOXYIK8Y"
    
    print(f"Sweeping for product {product_id} at {lat}, {lng} (radius 5km)...")
    
    # We will iterate through generator
    async for event in run_search(client, cache, product_id, lat, lng, radius_km=5.0, force=True):
        print("Event:", event["type"])
        if event["type"] == "store_result":
            print(f"  --> Store {event['store']['id']} Status: {event['status']} Price: {event['price']}")
        elif event["type"] == "home_result":
            print(f"  --> Home result. Serviceable: {event['serviceable']}")
        elif event["type"] == "error":
            print(f"  --> Error: {event.get('message')}")
        
    stats = cache.stats()
    print("Sweep complete. Cache stats:", stats)
    
    await client.aclose()
    cache.close()
    
if __name__ == "__main__":
    asyncio.run(main())
