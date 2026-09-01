import asyncio
import json
from app.platforms.zepto.client import ZeptoClient
from app.platforms.zepto.search import run_zepto_search

async def test_zepto_location(name: str, lat: float, lng: float, pvid: str):
    print(f"\n========== Testing {name} ==========")
    print(f"Coordinates: {lat}, {lng}")
    print(f"Product Variant ID: {pvid}")
    
    client = ZeptoClient()
    
    print("\nStarting search...")
    async for event in run_zepto_search(client, pvid, lat, lng, radius_km=3.0, force=True):
        print(f"\nReceived event type: {event.get('type')}")
        print(json.dumps(event, indent=2))
        
    await client.aclose()
    print(f"========== Finished {name} ==========\n")

async def main():
    pvid = "502699f1-3315-464a-9c71-066bc332e293"
    
    # Test 1: HSR Layout, Bengaluru (Usually Serviceable)
    await test_zepto_location(
        "HSR Layout, Bengaluru",
        12.9141, 77.6411,
        pvid
    )
    
    # Test 2: Kharar, Punjab (Usually Serviceable but different store)
    await test_zepto_location(
        "Kharar, Punjab",
        30.7415, 76.6521,
        pvid
    )

if __name__ == "__main__":
    asyncio.run(main())
