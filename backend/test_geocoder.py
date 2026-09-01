import asyncio
from app.store_cache import StoreCache
from app.geocoder import NominatimProvider

async def main():
    cache = StoreCache(":memory:")
    geocoder = NominatimProvider()
    
    # Test valid coords
    print("Testing Kharar coordinates...")
    res = await geocoder.reverse_geocode(30.7380, 76.6436)
    if res:
        print(f"Address: {res.formatted_address}")
        print(f"Confidence: {res.confidence}")
    else:
        print("Geocoding failed.")
        
    await geocoder.close()

if __name__ == "__main__":
    asyncio.run(main())
