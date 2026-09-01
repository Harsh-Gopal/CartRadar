import asyncio
from app.platforms.flipkart import FlipkartClient, FlipkartMinutesClient
import logging
logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing FlipkartClient...")
    c1 = FlipkartClient()
    res1 = await c1.product_at_location("ACCH6SR8QPWRQEGB", 12.9716, 77.5946)
    print("Flipkart Result:", res1)
    
    print("Testing FlipkartMinutesClient...")
    c2 = FlipkartMinutesClient()
    res2 = await c2.product_at_location("ACCH6SR8QPWRQEGB", 12.9716, 77.5946)
    print("Flipkart Minutes Result:", res2)

if __name__ == "__main__":
    asyncio.run(test())
