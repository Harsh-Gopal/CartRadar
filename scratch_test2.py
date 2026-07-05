import asyncio
from backend.app.platforms.bigbasket import BigBasketClient
from backend.app.platforms.blinkit import BlinkitClient
import sys

async def main():
    bb = BigBasketClient()
    blinkit = BlinkitClient()
    
    # 30.743, 76.657 is roughly Sector 126 Mohali
    lat, lng = 30.743, 76.657
    
    # Let's test BB
    bb_url = "https://www.bigbasket.com/pd/10000159/fresho-potato-1-kg/" 
    bb_product_id = "10000159"
    res = await bb.product_at_location(bb_product_id, lat, lng)
    print("BB Stock:", res)
        
    blinkit_url = "https://blinkit.com/prn/coca-cola-can/prid/11149"
    blinkit_product_id = "11149"
    res = await blinkit.product_at_location(blinkit_product_id, lat, lng)
    print("Blinkit Stock:", res)

    await bb.aclose()
    await blinkit.aclose()

if __name__ == "__main__":
    asyncio.run(main())
