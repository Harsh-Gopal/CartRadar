import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as c:
        resp = await c.get(
            "https://www.bigbasket.com/custompage/sysgen/?type=pc&slug=tata-salt",
            headers={"User-Agent": "Bigbasket-Android/8.0.5"}
        )
        print("Status", resp.status_code)
        print(resp.text[:500])

if __name__ == "__main__":
    asyncio.run(main())
