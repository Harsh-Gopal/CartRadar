import asyncio
import logging
from app.platforms.blinkit import BlinkitClient

logging.basicConfig(level=logging.DEBUG)

async def main():
    blinkit = BlinkitClient(concurrency=1)
    res = await blinkit.product_at_store("484783", "blinkit_30.738_76.655", lat=30.7379, lng=76.6551)
    print("Result:", res)
    await blinkit.aclose()

asyncio.run(main())
