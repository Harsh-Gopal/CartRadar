import asyncio
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.platforms.zepto.client import ZeptoPlaywrightSession

async def main():
    async with ZeptoPlaywrightSession() as session:
        points = [
            (28.6083, 77.2987), # Mayur Vihar
            (28.6749, 77.2941), # Shahdara
            (28.6317, 77.2832), # IP Extension
            (28.6552, 77.3605), # Indirapuram
        ]
        
        for lat, lng in points:
            res = await session.fast_sweep(lat, lng)
            print(f"Point {lat}, {lng} -> {res}")

if __name__ == "__main__":
    asyncio.run(main())
