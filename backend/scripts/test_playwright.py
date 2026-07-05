import asyncio
from playwright.async_api import async_playwright

async def run(playwright):
    browser = await playwright.chromium.launch()
    context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    page = await context.new_page()
    print("Navigating to BigBasket...")
    res = await page.goto('https://www.bigbasket.com/pd/241602/tata-salt-iodised-1-kg-pouch/', wait_until="domcontentloaded")
    print(f"Status: {res.status}")
    
    # Check if a WAF challenge is shown
    title = await page.title()
    print("Title:", title)
    content = await page.content()
    
    if "Access Denied" in title or "Security" in title or "Akamai" in content:
         print("Akamai Bot Manager blocked Playwright!")
    else:
         print("Bypassed BigBasket! HTML Length:", len(content))
         # wait for pricing to appear
         try:
             await page.wait_for_selector('td.L3_SellingPrice', timeout=3000)
             price = await page.text_content('td.L3_SellingPrice')
             print("Selling Price Element:", price)
         except Exception as e:
             print("Pricing element not found.", e)
             pass 

    await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

if __name__ == '__main__':
    asyncio.run(main())
