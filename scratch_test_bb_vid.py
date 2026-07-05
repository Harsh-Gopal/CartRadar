import asyncio
import httpx
import base64
import json
import re

async def main():
    async with httpx.AsyncClient() as c:
        # Step 1: Get initial cookies
        resp = await c.get("https://www.bigbasket.com/", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        print("Initial Cookies:", c.cookies)
        
        # Step 2: Set location cookies
        lat, lng = 30.743, 76.657
        pincode = "140301"
        area = "Sector 126"
        city = "Sahibzada Ajit Singh Nagar"
        
        lat_long_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}".encode()).decode().rstrip("=")
        addr_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}|{area}|{pincode}|{city}".encode()).decode().rstrip("=")
        
        c.cookies.set("_bb_lat_long", lat_long_b64, domain=".bigbasket.com")
        c.cookies.set("_bb_addressinfo", addr_b64, domain=".bigbasket.com")
        c.cookies.set("_bb_pin_code", pincode, domain=".bigbasket.com")
        
        # Step 3: Fetch product page
        url = "https://www.bigbasket.com/pd/10000159/fresho-potato-1-kg/"
        resp2 = await c.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "text/html"})
        
        # Parse NEXT_DATA
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp2.text, re.DOTALL)
        if m:
            state = json.loads(m.group(1))
            pd = state.get("props",{}).get("pageProps",{}).get("productDetails",{})
            children = pd.get("children", [])
            for child in children:
                if str(child.get("id")) == "10000159":
                    print("Found item!")
                    print("Availability:", child.get("availability"))
                    return
        print("Not found or no NEXT_DATA")

if __name__ == "__main__":
    asyncio.run(main())
