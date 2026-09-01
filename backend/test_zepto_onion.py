import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE
import json

async def main():
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6139, 77.2090)
        api_resp = await session.context.request.get(
            f"{BFF_BASE}/pds/v1/search?query=onion&storeId=0c865653-8eac-4a33-900c-d2ed7f3c0477",
            headers={"tenant": "ZEPTO"}
        )
        data = await api_resp.json()
        print(json.dumps(data, indent=2)[:500])

if __name__ == "__main__":
    asyncio.run(main())
