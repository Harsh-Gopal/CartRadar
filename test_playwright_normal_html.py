import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def main():
    url = "https://www.flipkart.com/realme-buds-wireless-5-50db-anc-360-degree-spatial-audio-ip55-38hrs-playback-bluetooth/p/itm98edfd0118e5a?pid=ACCH6SR8QPWRQEGB&marketplace=FLIPKART"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Try to find price
        price_div = soup.find("div", class_="Nx9bqj CxhGGd")
        if not price_div:
            # Another common class
            price_div = soup.find(text=lambda x: x and "₹" in x)
            
        print("Page content length:", len(content))
        
        # Flipkart often has ld+json for Product
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and "Product" in script.string:
                try:
                    data = json.loads(script.string)
                    # Handle if it's a list
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "Product":
                                print("Price from LD+JSON:", item.get("offers", {}).get("price"))
                                break
                    else:
                        print("Price from LD+JSON:", data.get("offers", {}).get("price"))
                except:
                    pass
                    
        await browser.close()

asyncio.run(main())
