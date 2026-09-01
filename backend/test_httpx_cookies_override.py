import asyncio
import httpx
from urllib.parse import quote
import json

async def run_trace():
    lat, lng = 28.6749, 77.2941
    position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
    
    async with httpx.AsyncClient() as client:
        # What happens to the cookie header?
        req = client.build_request(
            "HEAD",
            "https://www.zeptonow.com/",
            cookies={"user_position": position}
        )
        print("Cookies sent in header:")
        print(req.headers.get("cookie"))

if __name__ == "__main__":
    asyncio.run(run_trace())
