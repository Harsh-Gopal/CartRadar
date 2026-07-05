import asyncio
import json
import re
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    resp = await client._fetch_product_page("GARBAGE123", 30.7483, 76.6416)
    m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', resp.text)
    if m:
        state = json.loads(m.group(1))
        sd = state.get("storeDetailsV2", {})
        print("storeId:", sd.get("storeId"))
        ps = sd.get("primaryStore", {})
        od = ps.get("orderabilityDetails", {})
        print("serviceabilityStatus:", od.get("serviceabilityStatus"))
    else:
        print("No match")
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
