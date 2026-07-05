import asyncio
import httpx

async def main():
    url = "https://www.bigbasket.com/pd/10000159/fresho-potato-1-kg/"
    async with httpx.AsyncClient() as c:
        for ua in ["MegaFinderApp/1.0 (stock-checker)", "CartRadarApp/1.0 (stock-checker)", "Bigbasket-Android/8.0.5", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"]:
            resp = await c.get(url, headers={"User-Agent": ua, "Accept": "text/html"})
            print(f"[{ua}] {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
