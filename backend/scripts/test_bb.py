import asyncio
import httpx

# A basic test script to hit BigBasket's product page via Googlebot and Android UA
async def _fetch(ua: str, name: str):
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            "https://www.bigbasket.com/pd/241602/tata-salt-iodised-1-kg-pouch/",
            headers={"User-Agent": ua, "Accept": "text/html"}
        )
        print(f"[{name}] Status: {resp.status_code}")
        if resp.status_code == 200:
            if "tata-salt" in resp.text.lower():
                print(f"[{name}] Contains product text!")
            if "Next.js" in resp.text or "_next" in resp.text:
                print(f"[{name}] NextJS app framework identified")
        else:
            print(f"[{name}] Length: {len(resp.text)}")

async def main():
    print("Testing Googlebot...")
    await _fetch("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Googlebot")
    
    print("\nTesting Android App...")
    await _fetch("Bigbasket-Android/8.0.5", "AndroidApp")

if __name__ == "__main__":
    asyncio.run(main())
