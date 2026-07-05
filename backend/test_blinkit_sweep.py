import asyncio
import logging
from app.platforms.blinkit import BlinkitClient
import random

logging.basicConfig(level=logging.DEBUG)

async def main():
    blinkit = BlinkitClient(concurrency=5)
    
    # 484783 is Coca-Cola Zero Sugar
    product_id = "484783"
    
    # Central lat/lng
    center_lat, center_lng = 30.738, 76.655
    
    async def check(i):
        # vary lat/lng slightly
        lat = center_lat + random.uniform(-0.05, 0.05)
        lng = center_lng + random.uniform(-0.05, 0.05)
        store_id = f"blinkit_{round(lat, 3)}_{round(lng, 3)}"
        
        try:
            res = await blinkit.product_at_store(product_id, store_id, lat=lat, lng=lng)
            print(f"Task {i} finished: {res.status}")
        except Exception as e:
            print(f"Task {i} crashed: {e}")

    # Launch 20 concurrent checks
    tasks = [asyncio.create_task(check(i)) for i in range(20)]
    await asyncio.gather(*tasks)
    
    await blinkit.aclose()

asyncio.run(main())
