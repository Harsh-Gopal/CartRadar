import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession

async def run_trace():
    async with ZeptoPlaywrightSession() as session:
        # First probe HSR layout
        res1 = await session.probe_location(12.9141, 77.6411)
        print(f"HSR Layout: {res1.get('store_name')} ({res1.get('store_id')})")
        
        # Then probe Kharar
        res2 = await session.probe_location(30.7415, 76.6521)
        print(f"Kharar (contaminated): {res2.get('store_name')} ({res2.get('store_id')})")
        
if __name__ == "__main__":
    asyncio.run(run_trace())
