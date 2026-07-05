import asyncio
import re
import json
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    resp = await client._fetch_product_page("PSHOXYIK8Y", 28.6273928, 77.1716954)
    m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', resp.text)
    state = json.loads(m.group(1))
    
    sd = state.get("storeDetailsV2", {})
    print(json.dumps(sd, indent=2))
    
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
