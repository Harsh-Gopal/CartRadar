import asyncio
from app.platforms.blinkit import BlinkitClient

async def main():
    client = BlinkitClient()
    product_id = "11149" # Tetley Ginger... / Coca Cola
    lat, lng = 30.743, 76.657 # Sector 126, Mohali (140301)
    
    # This should trigger fetch
    res = await client.product_at_store(product_id, store_id="dummy", lat=lat, lng=lng)
    print("Result:", res)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
