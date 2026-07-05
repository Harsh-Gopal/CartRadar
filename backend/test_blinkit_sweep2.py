import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.DEBUG)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        
        try:
            async with page.expect_response("**/v1/layout/product/484783**", timeout=10000) as response_info:
                await page.goto("https://blinkit.com/prn/product/prid/484783", wait_until="domcontentloaded")
            
            response = await response_info.value
            body = await response.text()
            print("GOT BODY length:", len(body))
        except Exception as e:
            print("Timeout or error:", e)
            
        await browser.close()

asyncio.run(main())
