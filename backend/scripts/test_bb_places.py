import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            "https://www.bigbasket.com/places/v1/cities/places/?query=140301",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        print(resp.status_code)
        print(resp.text[:200])

if __name__ == "__main__":
    asyncio.run(main())
