import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession, BFF_BASE

async def main():
    pvid = "0651ed45-7cf6-453b-ba37-c5169094481c" # Paper Boat Zero
    
    loc_A = {"lat": 28.6139, "lng": 77.2090, "name": "Delhi"}
    loc_B = {"lat": 12.9121, "lng": 77.6446, "name": "HSR Layout, BLR"}
    
    store_A = "0c865653-8eac-4a33-900c-d2ed7f3c0477" # Mayur Vihar
    store_B = "7e5a1821-59ed-4d8a-8431-a3705afb22d2" # HSR
    
    async with ZeptoPlaywrightSession() as session:
        print("--- CONTEXT A ---")
        await session.probe_location(loc_A["lat"], loc_A["lng"])
        
        # Check Store A
        prod_A = await session.check_product(store_A, pvid)
        print(f"Store A (Context A) Price: {prod_A.price}, MRP: {prod_A.mrp}")
        
        # Check Store B (while in Context A)
        prod_B_ctx_A = await session.check_product(store_B, pvid)
        print(f"Store B (Context A) Price: {prod_B_ctx_A.price}, MRP: {prod_B_ctx_A.mrp}")
        
    async with ZeptoPlaywrightSession() as session2:
        print("--- CONTEXT B ---")
        await session2.probe_location(loc_B["lat"], loc_B["lng"])
        
        # Check Store B (while in Context B)
        prod_B_ctx_B = await session2.check_product(store_B, pvid)
        print(f"Store B (Context B) Price: {prod_B_ctx_B.price}, MRP: {prod_B_ctx_B.mrp}")

if __name__ == "__main__":
    asyncio.run(main())
