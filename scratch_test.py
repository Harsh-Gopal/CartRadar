import asyncio
from backend.app.platforms.bigbasket import BigBasketClient
from backend.app.platforms.blinkit import BlinkitClient
import sys

async def main():
    bb = BigBasketClient()
    blinkit = BlinkitClient()
    
    # We will need some test URLs and lat/lng
    bb_url = "https://www.bigbasket.com/pd/10000159/fresho-potato-1-kg/" 
    bb_product_id = await bb.resolve_share_link(bb_url)
    print("Parsed BB ID:", bb_product_id)
    if bb_product_id:
        # Kharar coordinates (approx)
        lat, lng = 30.7410, 76.6500
        res = await bb.product_at_location(bb_product_id, lat, lng)
        print("BB Stock:", res)
        
    blinkit_url = "https://blinkit.com/prn/coca-cola-can/prid/11149"
    blinkit_product_id = await blinkit.resolve_share_link(blinkit_url)
    print("Parsed Blinkit ID:", blinkit_product_id)
    if blinkit_product_id:
        # Kharar coordinates
        lat, lng = 30.7410, 76.6500
        res = await blinkit.product_at_location(blinkit_product_id, lat, lng)
        print("Blinkit Stock:", res)

    await bb.aclose()
    await blinkit.aclose()

if __name__ == "__main__":
    asyncio.run(main())
