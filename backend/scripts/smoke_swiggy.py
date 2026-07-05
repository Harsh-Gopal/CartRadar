import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    ) as client:
        # Step 1: get initial cookies
        resp = await client.get("https://www.swiggy.com/")
        print("Swiggy homepage status:", resp.status_code)
        
        # Step 2: Try to find a dark store endpoint
        # The typical way Swiggy sets location is by calling an update location API or sending coordinates.
        # Let's search Swiggy for an item or look at what APIs they might have.
        # We can try to geocode first:
        geo_resp = await client.get(
             "https://www.swiggy.com/dapi/misc/place-autocomplete?input=560001&types="
        )
        print("Geocode:", geo_resp.status_code, geo_resp.text[:200])

if __name__ == "__main__":
    asyncio.run(main())
