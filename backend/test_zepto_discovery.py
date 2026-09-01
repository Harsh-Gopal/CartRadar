import asyncio
import logging
from app.search import run_search
from app.store_cache import StoreCache
from app.platforms.zepto import ZeptoClient

logging.basicConfig(level=logging.INFO)

async def test_discovery():
    client = ZeptoClient()
    cache = StoreCache(":memory:")
    lat, lng = 12.9141, 77.6411 # HSR Layout
    radius = 5.0
    product_id = "502699f1-3315-464a-9c71-066bc332e293"

    print("Running Zepto search on HSR Layout...")
    gen = run_search(client, cache, product_id, lat, lng, radius)
    async for event in gen:
        print("Event:", event["type"])
        if event["type"] == "store_result":
            print(f"  Store: {event['store']['name']} ({event['status']})")
        elif event["type"] == "discovery_start":
            print(f"  Probing {event['points_to_probe']} points...")
        if event["type"] == "zepto_result":
            import json
            print("  Zepto Result:", json.dumps(event, indent=2))
        elif event["type"] == "done":
            print("  Summary:", event.get("summary"))

if __name__ == "__main__":
    asyncio.run(test_discovery())
