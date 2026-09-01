import asyncio
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    # Maggi 2-Minute Noodles - 420g
    res = await client.product_at_store("a52b827e-85a7-47b8-8094-0f2c417da558", "332822", lat=12.92, lng=77.62)
    print("Swiggy result:", res)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
