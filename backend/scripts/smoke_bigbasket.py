import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    ) as client:
        # Step 1: get initial cookies
        resp = await client.get("https://www.bigbasket.com/")
        print("BB homepage status:", resp.status_code)
        
        # Geocode/autocomplete to get a location
        geo_resp = await client.get(
             "https://www.bigbasket.com/places/v1/cities/places/?query=560001"
        )
        print("Geocode:", geo_resp.status_code, geo_resp.text[:300])

if __name__ == "__main__":
    asyncio.run(main())
