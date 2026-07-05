import asyncio
import httpx
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    tasks = []
    
    async def _fetch(i):
        # vary the lat/lng slightly
        lat = 28.6273928 + (i * 0.001)
        res = await client._fetch_product_page("PSHOXYIK8Y", lat, 77.1716954)
        print(f"[{i}] len: {len(res.text)}")
    
    for i in range(20):
        tasks.append(_fetch(i))
        
    await asyncio.gather(*tasks)
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
