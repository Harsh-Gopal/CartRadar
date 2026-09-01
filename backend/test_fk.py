import asyncio
from app.platforms.flipkart import FlipkartClient, FlipkartMinutesClient

async def main():
    print("Testing Normal Flipkart Client")
    normal_client = FlipkartClient()
    normal_product = await normal_client.product_at_location("TPSH3PYAHTQEGTGF", 28.6139, 77.2090)
    print("Normal Product:", normal_product)
    await normal_client.aclose()

    print("\nTesting Flipkart Minutes Client")
    fm_client = FlipkartMinutesClient()
    # Need to run resolve_store first because product_at_store expects serviceable
    res = await fm_client.resolve_store(28.6139, 77.2090, "TPSH3PYAHTQEGTGF")
    print("Resolve:", res)
    # The URL from the prompt is HYPERLOCAL marketplace
    # Wait, the prompt says: "Make sure the same product image appears in the Product card... Trace the actual product-image extraction/normalization pipeline for Flipkart Minutes and all other platforms."
    
    # In main.py, resolve_link uses `client.product_at_store(product_id, "dummy", 28.6139, 77.2090)` if coords are missing.
    # Let's test that directly:
    fm_product = await fm_client.product_at_store("TPSH3PYAHTQEGTGF", "dummy", 28.6139, 77.2090)
    print("FM Product:", fm_product)
    await fm_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
