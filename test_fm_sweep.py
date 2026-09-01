import asyncio
import logging
from backend.app.platforms.flipkart import FlipkartMinutesClient
from backend.app.store_cache import StoreCache
from backend.app.search import run_search

logging.basicConfig(level=logging.INFO)

async def main():
    client = FlipkartMinutesClient()
    cache = StoreCache(":memory:")
    
    print("Testing radius sweep for Flipkart Minutes (Patna) with radius 10.0...")
    
    async for event in run_search(client, cache, "TPSH3PYAHTQEGTGF", lat=25.601, lng=85.07, radius_km=10.0):
        if event["type"] in ["discovery_start", "discovery_progress", "done"]:
            print("EVENT:", event)
        
if __name__ == "__main__":
    asyncio.run(main())
