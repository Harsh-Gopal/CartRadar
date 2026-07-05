import asyncio
from app.platforms.bigbasket import BigBasketClient

async def main():
    client = BigBasketClient()
    product_id = "10000159" # Potato
    lat, lng = 30.743, 76.657 # Sector 126, Mohali (140301)
    
    # This should trigger session init, then fetch product
    res = await client.product_at_store(product_id, store_id="dummy", lat=lat, lng=lng)
    print("Result:", res)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
