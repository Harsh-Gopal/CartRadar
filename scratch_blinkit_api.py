import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as c:
        product_id = "11149"
        lat, lng = "30.743", "76.657"
        url = f"https://blinkit.com/v1/layout/product/{product_id}"
        
        headers = {
            "User-Agent": "Blinkit/11.40.1 (Android; 14)",
            "lat": lat,
            "lon": lng,
            "app_client": "consumer_app"
        }
        resp = await c.get(url, headers=headers)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            print("BODY:", resp.text[:500])
        else:
            print("ERROR BODY:", resp.text)

if __name__ == "__main__":
    asyncio.run(main())
