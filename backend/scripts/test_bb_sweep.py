import asyncio
from app.platforms.bigbasket import BigBasketClient

async def main():
    client = BigBasketClient()
    res = await client.resolve_store(28.6273928, 77.1716954, "10000148")
    print(res)
    if res.serviceable:
        prod = await client.product_at_store("10000148", res.store_id, 28.6273928, 77.1716954)
        print(prod)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
