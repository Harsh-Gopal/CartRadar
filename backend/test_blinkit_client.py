import asyncio
import logging
from app.platforms.blinkit import BlinkitClient

logging.basicConfig(level=logging.DEBUG)

async def main():
    blinkit = BlinkitClient(concurrency=1)
    # enable verbose logging in Playwright fetch
    res = await blinkit.product_at_store("blinkit_30.738_76.655", "484783")
    print("Result:", res)
    await blinkit.aclose()

asyncio.run(main())
