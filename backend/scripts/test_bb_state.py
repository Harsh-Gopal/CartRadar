import asyncio
import json
import re
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.bigbasket.com/pd/241602/", wait_until="networkidle")
        content = await page.content()
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', content, re.DOTALL)
        if m:
            state = json.loads(m.group(1))
            with open("bb_playwright_state.json", "w") as f:
                json.dump(state, f, indent=2)
            print("Wrote bb_playwright_state.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
