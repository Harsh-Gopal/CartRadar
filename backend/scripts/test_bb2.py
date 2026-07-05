import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            "https://www.bigbasket.com/pd/241602/tata-salt-iodised-1-kg-pouch/",
            headers={"User-Agent": "Bigbasket-Android/8.0.5", "Accept": "text/html"}
        )
        with open("bb_android_resp.html", "w") as f:
            f.write(resp.text)
        print("Wrote bb_android_resp.html")

if __name__ == "__main__":
    asyncio.run(main())
