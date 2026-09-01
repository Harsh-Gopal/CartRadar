import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    # Use the real Coke product URL:
    product_url = "https://www.zeptonow.com/pn/coca-cola-pet-cola-sparkling-soft-drink/pvid/c44ec4ef-f2e8-466d-ad50-13adcdb80267"
    
    # 28.6139, 77.2090 is Central Delhi. Let's use something specific like Shadara: 28.6811, 77.2917
    # Or just use Kharar: 30.7333, 76.7794
    # Wait, the user mentioned Coca-Cola PET Cola
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Go to Zepto to get WAF cookies
        await page.goto("https://www.zeptonow.com/")
        await page.wait_for_timeout(3000)
        
        # Set location to Shadara (Delhi)
        await page.evaluate('''() => {
            localStorage.setItem('addressContext', JSON.stringify({
                "latitude": 28.6811,
                "longitude": 77.2917,
                "address": "Shahdara, Delhi"
            }));
            document.cookie = "user_position=28.6811,77.2917; path=/";
        }''')
        await page.reload()
        await page.wait_for_timeout(3000)
        
        # Capture API responses
        api_responses = {}
        async def handle_response(response):
            if "product-detail" in response.url or "v1/search" in response.url or "product-assortment" in response.url:
                try:
                    data = await response.json()
                    api_responses[response.url] = data
                except:
                    pass
        page.on("response", handle_response)
        
        # Go to product page
        await page.goto(product_url)
        await page.wait_for_timeout(5000)
        
        # Extract price from DOM
        try:
            # Attempt to find the price element in the DOM
            # Zepto uses data-testid="product-price" or similar. Let's dump all text that looks like a price
            price_text = await page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('*'));
                for(const el of els) {
                    if (el.innerText && el.innerText.includes('₹') && el.tagName.match(/^H[1-6]|SPAN|DIV|P$/)) {
                        // just return the whole body text to be safe
                        return document.body.innerText;
                    }
                }
                return document.body.innerText;
            }''')
            print("DOM contains price info? (Check lengths/keywords)")
            lines = [l for l in price_text.split('\n') if '₹' in l]
            print("DOM Price lines:", lines)
        except Exception as e:
            print("DOM Price Error:", e)
            
        print("API Responses keys:")
        for url, data in api_responses.items():
            print(url)
            # Find sellingPrice
            try:
                if 'productVariant' in str(data):
                    print("Found product variant in API!")
            except:
                pass
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
