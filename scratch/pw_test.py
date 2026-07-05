import asyncio
from playwright.async_api import async_playwright

async def test_pw():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Mock location or just visit
        resp = await page.goto("https://blinkit.com/pr/tata-tea-gold/prid/10532", wait_until="domcontentloaded")
        print("Status:", resp.status)
        content = await page.content()
        import re
        import json
        match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});', content)
        if not match:
            match = re.search(r'window\.grofers\s*=\s*(\{.*?\});', content)
        
        if match:
            print("Found state!")
            j = json.loads(match.group(1))
            try:
                bff = j["PRELOADED_STATE"]["ui"]["pdp"]["bffPdp"]["bffData"]
                p = bff.get("product")
                if p:
                    print("Product name:", p.get("name"))
            except Exception as e:
                print(e)
        else:
            print("Not found in content")
        await browser.close()

asyncio.run(test_pw())
