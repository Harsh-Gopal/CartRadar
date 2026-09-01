import asyncio
import httpx
from urllib.parse import quote
import json

async def run_trace():
    lat, lng = 28.6749, 77.2941
    position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
    
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            "HEAD",
            "https://www.zeptonow.com/",
            headers={
                "Accept": "text/html",
                "Cookie": f"user_position={position}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        )
        print(f"Status: {resp.status_code}")
        print("Cookies:")
        for name, value in resp.cookies.items():
            print(f"- {name}: {value[:50]}...")
            
if __name__ == "__main__":
    asyncio.run(run_trace())
