import asyncio
import httpx
import re
import json
from app.platforms.swiggy import SwiggyClient

async def main():
    async with httpx.AsyncClient() as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept": "text/html"
        }
        loc_cookie = '{"lat":28.6273928,"lng":77.1716954,"address":""}'
        res = await client.get("https://www.swiggy.com/instamart", headers=headers, cookies={"userLocation": loc_cookie})
        
        print("Status", res.status_code)
        print("Length", len(res.text))
        
        m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', res.text)
        if m:
            state = json.loads(m.group(1))
            sd = state.get("storeDetailsV2", {})
            print("Store ID:", sd.get("storeId"))
        else:
            print("No state found!")
            
if __name__ == "__main__":
    asyncio.run(main())
