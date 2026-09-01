import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession
import sys
import json
from bs4 import BeautifulSoup

async def main():
    pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70"
    url = f"https://www.zeptonow.com/pn/product/pvid/{pvid}"
    
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6083, 77.2987)
        page = session.page
        await page.goto(url, wait_until="domcontentloaded")
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check Next.js data
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            data = json.loads(next_data.string)
            print("Found __NEXT_DATA__!")
            # Try to find image in props
            try:
                page_props = data['props']['pageProps']
                # Dump keys to see what's available
                print("PageProps keys:", page_props.keys())
                
                # Check for product info
                if 'initialState' in page_props:
                    print("Has initialState")
            except Exception as e:
                print(e)
                
        # Also check meta tags
        og_image = soup.find('meta', property='og:image')
        print("OG Image:", og_image['content'] if og_image else "None")

if __name__ == "__main__":
    asyncio.run(main())
