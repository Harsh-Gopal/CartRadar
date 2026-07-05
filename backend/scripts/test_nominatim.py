import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as c:
        try:
            resp = await c.get(
                "https://nominatim.openstreetmap.org/reverse?lat=28.6273928&lon=77.1716954&format=json",
                headers={"User-Agent": "StockChecker (github.com)"}
            )
            data = resp.json()
            address = data.get("address", {})
            suburb = address.get("suburb", "")
            postcode = address.get("postcode", "")
            city = address.get("city", address.get("town", ""))
            
            label = ", ".join(filter(bool, [suburb, city, postcode]))
            print(f"Address: {label}")
        except Exception as e:
            print("Error", e)

if __name__ == "__main__":
    asyncio.run(main())
