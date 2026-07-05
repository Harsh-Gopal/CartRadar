import asyncio
from app.platforms.zepto import ZeptoClient

async def main():
    z = ZeptoClient()
    res = await z.resolve_store(28.6273928, 77.1716954)
    print(res)
    await z.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
