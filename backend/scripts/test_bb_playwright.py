import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        resp = await page.goto("https://www.bigbasket.com/pd/241602/", wait_until="domcontentloaded")
        print("Status", resp.status)
        
        content = await page.content()
        import re
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', content, re.DOTALL)
        if m:
            print("Found NEXT DATA")
            state = json.loads(m.group(1))
            pd = state.get("props",{}).get("pageProps",{}).get("productDetails",{}).get("children",[])
            print("Children length:", len(pd))
        else:
            print("NEXT DATA NOT FOUND")
            print("Access denied?" if "Access Denied" in content else "Other HTML")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
