import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE

async def main():
    pvid = "5c52c286-90f7-4184-be2f-48d948be3855" # Need the real coke PVID
    
    # First search for coke
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6139, 77.2090)
        api_resp = await session.context.request.get(
            f"{BFF_BASE}/pds/v1/search?query=coca+cola+pet&storeId=0c865653-8eac-4a33-900c-d2ed7f3c0477",
            headers={"tenant": "ZEPTO"}
        )
        data = await api_resp.json()
        print(data.keys())

if __name__ == "__main__":
    asyncio.run(main())
