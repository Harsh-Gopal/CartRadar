import asyncio
from backend.app.platforms.zepto.client import ZeptoPlaywrightSession
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    pvid = "17bc2d44-d9bc-43cf-be81-797587123fa3"
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6083, 77.2987)
        res = await session.check_product("0c865653-8eac-4a33-900c-d2ed7f3c0477", pvid)
        print(f"Product: {res.name}")
        print(f"Image: {res.image_url}")

if __name__ == "__main__":
    asyncio.run(main())
