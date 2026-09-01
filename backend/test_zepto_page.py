import asyncio
import httpx
from bs4 import BeautifulSoup

async def main():
    pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70"
    url = f"https://www.zeptonow.com/pn/product/pvid/{pvid}"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        og_title = soup.find('meta', property='og:title')
        
        print("Status:", resp.status_code)
        print("Title:", og_title['content'] if og_title else None)
        print("Image:", og_image['content'] if og_image else None)
        
if __name__ == "__main__":
    asyncio.run(main())
