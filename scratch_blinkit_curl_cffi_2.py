import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    async with AsyncSession(impersonate="chrome110") as s:
        product_id = "11149"
        lat, lng = "30.743", "76.657"
        url = f"https://blinkit.com/v1/layout/product/{product_id}"
        
        headers = {
            "lat": lat,
            "lon": lng,
            "app_client": "consumer_web"
        }
        resp = await s.get(url, headers=headers)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            print("BODY:", resp.text[:500])
        else:
            print("ERROR BODY:", resp.text[:500])

if __name__ == "__main__":
    asyncio.run(main())
