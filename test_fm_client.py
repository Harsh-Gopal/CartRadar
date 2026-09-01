import asyncio
from backend.app.platforms.flipkart import FlipkartMinutesClient

async def main():
    client = FlipkartMinutesClient()
    print("Testing unserviceable location (Shimla)...")
    res = await client.resolve_store(31.1048, 77.1734, "TPSH3PYAHTQEGTGF")
    print(res)
        
if __name__ == "__main__":
    asyncio.run(main())
