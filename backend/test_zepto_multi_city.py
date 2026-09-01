import asyncio
import logging
from app.store_cache import StoreCache
from app.platforms.zepto.client import ZeptoClient
from app.platforms.zepto.search import run_zepto_search

logging.basicConfig(level=logging.WARNING)

async def test_city(city_name, lat, lng, pvid, cache, client):
    print(f"\n========== Testing {city_name} (3km Sweep) ==========")
    async for event in run_zepto_search(client, pvid, lat, lng, radius_km=3.0, cache=cache):
        if event['type'] == 'store_result':
            print(f"Store: {event['store']['name']} ({event['store']['id']}) - Distance: {event['distance_km']:.2f}km - Status: {event['status']} - Price: {event.get('price')} MRP: {event.get('mrp')}")
        elif event['type'] == 'discovery_start':
            print(f"Discovery Started: {event['points_to_probe']} points to probe, {event['cached_stores']} cached stores found.")

async def run_test():
    client = ZeptoClient()
    # Use a fresh cache
    cache = StoreCache("test_zepto_multi.db")
    
    # We will use the Colgate Visible White Purple PVID used in UI: 
    # Actually, we don't know the Zepto PVID for Colgate from the user's prompt (they gave Flipkart link).
    # Let's use the generic Paper Boat Coffee PVID (0651ed45-7cf6-453b-ba37-c5169094481c) or some known product.
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c"
    
    await test_city("Kharar, Punjab", 30.7415, 76.6521, pvid, cache, client)
    await test_city("HSR Layout, Bengaluru", 12.9141, 77.6411, pvid, cache, client)
    await test_city("Shahdara, Delhi", 28.6749, 77.2941, pvid, cache, client)

if __name__ == "__main__":
    asyncio.run(run_test())
