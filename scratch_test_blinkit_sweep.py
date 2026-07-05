import asyncio
from app.platforms.blinkit import BlinkitClient
from app.grid import hex_grid

async def main():
    client = BlinkitClient(concurrency=8)
    product_id = "11149" # Tetley / Coca Cola
    
    # 30km grid
    lat, lng = 30.743, 76.657
    points = hex_grid(lat, lng, 30.0, 3.0)
    print("Points in 30km grid:", len(points))
    
    async def check(p):
        plat, plng = p
        return await client.product_at_store(product_id, store_id="dummy", lat=plat, lng=plng)
        
    tasks = [check(p) for p in points[:30]] # Test first 30 points to not take forever
    results = await asyncio.gather(*tasks)
    errors = sum(1 for r in results if r.status == "error")
    print(f"Total: {len(results)}, Errors: {errors}")
    await client.aclose()
    
    import sys
    # Ensure playwright stops properly so script exits
    from app.platforms.blinkit import _close_browser
    await _close_browser()

if __name__ == "__main__":
    asyncio.run(main())
