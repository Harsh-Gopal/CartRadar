import asyncio
import httpx
import re
import json

async def test():
    url = "https://www.bigbasket.com/pd/10000148/"
    headers = {
        "Accept": "text/html",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as c:
        resp = await c.get(url, headers=headers)
        print("Status:", resp.status_code)
        print("Size:", len(resp.text))
        
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            pd = data.get("props",{}).get("pageProps",{}).get("productDetails",{})
            children = pd.get("children", [])
            print("Children count:", len(children))
        else:
            print("No NEXT DATA")

if __name__ == "__main__":
    asyncio.run(test())
