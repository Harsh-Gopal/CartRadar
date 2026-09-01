import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession
from bs4 import BeautifulSoup

async def main():
    pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70"
    url = f"https://www.zeptonow.com/pn/product/pvid/{pvid}"
    
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6083, 77.2987)
        resp = await session.context.request.get(url, timeout=10000)
        print("Status:", resp.status)
        html = await resp.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        og_title = soup.find('meta', property='og:title')
        
        print("Title:", og_title['content'] if og_title else None)
        print("Image:", og_image['content'] if og_image else None)

if __name__ == "__main__":
    asyncio.run(main())
