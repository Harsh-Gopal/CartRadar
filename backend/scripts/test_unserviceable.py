import asyncio
import json
import re
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    # Middle of nowhere (mountains)
    resp = await client._fetch_product_page("PSHOXYIK8Y", 31.1, 77.1)
    m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', resp.text)
    if m:
        state = json.loads(m.group(1))
        sd = state.get("storeDetailsV2")
        print("storeDetailsV2 type:", type(sd))
        if sd is None:
            print("storeDetailsV2 is explicitly null")
        else:
            print(json.dumps(sd, indent=2))
    else:
        print("No match")
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
