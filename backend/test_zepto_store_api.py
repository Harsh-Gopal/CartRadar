import asyncio
import httpx

async def run_trace():
    async with httpx.AsyncClient() as client:
        # Try some common patterns
        urls = [
            "https://bff-gateway.zepto.com/api/v1/store/444a442d-982b-437d-a8eb-9ca9385eaed5",
            "https://api.zeptonow.com/api/v1/store/444a442d-982b-437d-a8eb-9ca9385eaed5",
            "https://api.zeptonow.com/api/v1/config/layout/?storeId=444a442d-982b-437d-a8eb-9ca9385eaed5"
        ]
        
        for url in urls:
            resp = await client.get(url, headers={"platform": "WEB", "tenant": "ZEPTO", "app_version": "16.2.11"})
            print(f"{url} -> {resp.status_code}")
            if resp.status_code == 200:
                print(resp.text[:200])

if __name__ == "__main__":
    asyncio.run(run_trace())
