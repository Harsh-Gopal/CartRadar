import asyncio
import logging
from app.store_cache import StoreCache
from app.platforms.zepto.client import ZeptoClient
from app.platforms.zepto.search import run_zepto_search

logging.basicConfig(level=logging.WARNING)

async def run_test():
    client = ZeptoClient()
    cache = StoreCache("test_zepto.db")
    
    print("\n========== Testing Kharar, Punjab (3km Sweep) First Time ==========")
    lat, lng = 30.7415, 76.6521
    pvid = "502699f1-3315-464a-9c71-066bc332e293"
    
    async for event in run_zepto_search(client, pvid, lat, lng, radius_km=3.0, cache=cache):
        if event['type'] == 'store_result':
            print(f"Store: {event['store']['name']} ({event['store']['id']}) - Distance: {event['distance_km']:.2f}km - Status: {event['status']}")
        elif event['type'] == 'discovery_start':
            print(f"Discovery Started: {event['points_to_probe']} points to probe, {event['cached_stores']} cached stores found.")
            
    print("\n========== Testing Kharar, Punjab (3km Sweep) Second Time (Cached) ==========")
    async for event in run_zepto_search(client, pvid, lat, lng, radius_km=3.0, cache=cache):
        if event['type'] == 'store_result':
            print(f"Store: {event['store']['name']} ({event['store']['id']}) - Distance: {event['distance_km']:.2f}km - Status: {event['status']}")
        elif event['type'] == 'discovery_start':
            print(f"Discovery Started: {event['points_to_probe']} points to probe, {event['cached_stores']} cached stores found.")
            
if __name__ == "__main__":
    asyncio.run(run_test())
