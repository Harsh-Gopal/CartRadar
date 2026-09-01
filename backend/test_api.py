import asyncio
from app.main import app
from httpx import AsyncClient, ASGITransport

async def test_resolve():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        print("Testing resolve_link for Flipkart Minutes")
        response = await ac.post(
            "/api/resolve", 
            json={
                "url": "https://www.flipkart.com/colgate-visible-white-purple-color-correcting-toothpaste/p/itm147dbf159b039?pid=TPSH3PYAHTQEGTGF&marketplace=HYPERLOCAL",
                "lat": 25.601,
                "lng": 85.070
            }
        )
        print("Status Code:", response.status_code)
        import json
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_resolve())
