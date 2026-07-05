import asyncio
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    print("Testing Swiggy Product Extraction for PSHOXYIK8Y...")
    res = await client.product_at_location("PSHOXYIK8Y", 28.6273928, 77.1716954)
    print("Result:", res)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
