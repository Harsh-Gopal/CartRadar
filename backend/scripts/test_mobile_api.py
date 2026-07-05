import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        android_headers = {
            "User-Agent": "Bigbasket-Android/8.0.5",
            "Accept": "application/json"
        }
        res2 = await client.get("https://app.bigbasket.com/product/v4/product-info/241602/", headers=android_headers)
        print("BB App API HTTP status:", res2.status_code)
        
if __name__ == "__main__":
    asyncio.run(main())
