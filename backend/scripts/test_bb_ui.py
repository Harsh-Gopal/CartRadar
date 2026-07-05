import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Going to homepage...")
        await page.goto("https://www.bigbasket.com/")
        
        print("Clicking location...")
        try:
            # Click the location dropdown in header
            await page.locator("button.AddressDropdown___StyledMenuButton-sc-17g6m4-1").click(timeout=5000)
            
            # Wait for search input
            await page.locator("input[placeholder='Search for area or street name']").fill("110001", timeout=5000)
            
            # Click the first suggestion
            await page.locator("div.mt-5.flex.cursor-pointer").first.click(timeout=5000)
            
            print("Location set!")
            await page.wait_for_timeout(2000)
            
            print("Cookies:")
            cookies = await page.context.cookies()
            for c in cookies:
                if c["name"].startswith("_bb_"):
                    print(f"{c['name']}: {c['value']}")
        except Exception as e:
            print("UI automation failed:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
