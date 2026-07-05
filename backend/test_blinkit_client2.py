import asyncio
import logging
from app.platforms.blinkit import BlinkitClient

logging.basicConfig(level=logging.DEBUG)

async def main():
    blinkit = BlinkitClient(concurrency=1)
    res = await blinkit._fetch_product_via_playwright("484783", 30.7379, 76.6551)
    print("Result JSON keys:", res.keys() if res else None)
    await blinkit.aclose()

asyncio.run(main())
