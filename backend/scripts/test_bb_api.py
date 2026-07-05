import asyncio
import httpx

async def try_api(name, url, method="GET", json=None):
    async with httpx.AsyncClient() as c:
        try:
            if method == "GET":
                resp = await c.get(url, headers={"User-Agent": "Bigbasket-Android/8.0.5"})
            else:
                resp = await c.post(url, headers={"User-Agent": "Bigbasket-Android/8.0.5"}, json=json)
            print(f"[{name}] {resp.status_code}")
            if resp.status_code == 200:
                print(resp.text[:200])
        except Exception as e:
            print(f"[{name}] Error: {e}")

async def main():
    await try_api("bb-getProductData", "https://www.bigbasket.com/product/get-products/?slug=tata-salt")
    await try_api("bb-internal", "https://internal.bigbasket.com/api/v1/products/241602/")
    
if __name__ == "__main__":
    asyncio.run(main())
