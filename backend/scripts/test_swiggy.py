import asyncio
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    print("Testing Swiggy Product Extraction...")
    res = await client.product_at_location("5R2M1GC5V0", 12.9100, 77.6300)
    print("Result:", res)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
