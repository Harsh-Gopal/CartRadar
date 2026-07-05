import asyncio
import httpx

async def f():
    resp = await httpx.AsyncClient().get(
        "https://www.bigbasket.com/product/v1/product/get-info/?pd_id=241602",
        headers={"User-Agent": "Bigbasket-Android/8.0.5"}
    )
    print(resp.status_code)
    print(resp.text[:200])

if __name__ == "__main__":
    asyncio.run(f())
