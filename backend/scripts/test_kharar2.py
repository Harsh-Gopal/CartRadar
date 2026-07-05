import asyncio
from app.platforms.swiggy import SwiggyClient

async def main():
    client = SwiggyClient()
    # 30.747, 76.642 approximate kharar
    res = await client.resolve_store(30.7483, 76.6416, "PSHOXYIK8Y")
    print(res)
    await client.aclose()
    
if __name__ == "__main__":
    asyncio.run(main())
