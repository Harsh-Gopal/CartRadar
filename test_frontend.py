import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:5173/")
        print("Page loaded")
        
        # Type in search URL
        await page.fill('input[type="text"]', 'https://www.swiggy.com/stores/instamart/item/2NFSYH6XCW')
        await page.keyboard.press("Enter")
        
        await asyncio.sleep(2)
        
        # Click search button or location button if needed
        # The app might auto-resolve, then show "Search nearby stores anyway"
        try:
            btn = page.locator('button:has-text("Search nearby")')
            if await btn.is_visible():
                await btn.click()
                print("Clicked search nearby")
        except Exception:
            pass
            
        # Wait 15 seconds to see what happens
        await asyncio.sleep(15)
        
        # Check if loading indicator is still present
        html = await page.content()
        if "Checking delivery" in html or "animate-pulse" in html or "searching" in html:
            print("Still loading")
        else:
            print("Finished loading")
            
        # Print all errors from console
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
