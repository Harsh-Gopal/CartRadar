import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        page.on("console", lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"JS ERROR: {err}"))

        await page.goto("http://localhost:5173/")
        print("Page loaded")
        
        await page.fill('input[type="url"]', 'https://www.swiggy.com/stores/instamart/item/2NFSYH6XCW')
        await asyncio.sleep(2)
        
        try:
            btn = page.locator('button:has-text("Search nearby")')
            if await btn.is_visible():
                await btn.click()
                print("Clicked search nearby")
        except Exception:
            pass
            
        await asyncio.sleep(15)
        
        html = await page.content()
        if "Checking delivery" in html or "animate-pulse" in html:
            print("Still loading")
        else:
            print("Finished loading")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
