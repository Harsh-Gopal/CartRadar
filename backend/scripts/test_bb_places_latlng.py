import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as c:
        resp = await c.get("https://www.bigbasket.com/places/v1/cities/places/?lat=28.6273928&lng=77.1716954")
        print(resp.status_code)
        print(resp.text[:500])

if __name__ == "__main__":
    asyncio.run(main())
