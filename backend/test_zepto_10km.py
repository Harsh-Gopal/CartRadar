import asyncio
import logging
from backend.app.platforms.zepto.client import ZeptoClient
from backend.app.platforms.zepto.search import run_zepto_search
from backend.app.store_cache import StoreCache

logging.basicConfig(level=logging.INFO)

async def main():
    client = ZeptoClient()
    cache = StoreCache(":memory:")
    
    lat, lng = 28.6083, 77.2987
    radius_km = 10.0
    
    print(f"Starting 10km sweep around Mayur Vihar ({lat}, {lng})")
    
    async for event in run_zepto_search(client, "17bc2d44-d9bc-43cf-be81-797587123fa3", lat, lng, radius_km, cache):
        if event["type"] == "store_result":
            store = event["store"]
            print(f"Found store: {store['name']} ({store['id']}) at {store['lat']}, {store['lng']} - Dist: {event['distance_km']}")
        elif event["type"] in ("discovery_start", "discovery_progress", "error"):
            print(event)

if __name__ == "__main__":
    asyncio.run(main())
