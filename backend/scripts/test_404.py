import asyncio
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    resp = await client._fetch_product_page("GARBAGE123", 28.627, 77.171)
    print("Status:", resp.status_code)
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
