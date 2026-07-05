import asyncio
import sys
from app.platforms.bigbasket import BigBasketClient

async def test():
    bb = BigBasketClient()
    res = await bb.product_at_location("40124370", 28.6273928, 77.1716954)
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
