import asyncio
from playwright.async_api import async_playwright
import base64
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Setup context with location
        lat, lng = 30.743, 76.657
        pincode = "140301"
        area = "Sector 126"
        city = "Sahibzada Ajit Singh Nagar"
        
        lat_long_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}".encode()).decode().rstrip("=")
        addr_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}|{area}|{pincode}|{city}".encode()).decode().rstrip("=")
        
        context = await browser.new_context()
        await context.add_cookies([
            {"name": "_bb_lat_long", "value": lat_long_b64, "domain": ".bigbasket.com", "path": "/"},
            {"name": "_bb_addressinfo", "value": addr_b64, "domain": ".bigbasket.com", "path": "/"},
            {"name": "_bb_pin_code", "value": pincode, "domain": ".bigbasket.com", "path": "/"},
        ])
        
        page = await context.new_page()
        
        # intercept responses
        async def handle_response(response):
            try:
                print(f"[{response.status}] {response.url}")
                if "api" in response.url or "v1" in response.url or "graphql" in response.url:
                    text = await response.text()
                    print(f"BODY: {text[:500]}\n")
            except:
                pass

        page.on("response", handle_response)
        
        print("Navigating...")
        await page.goto("https://www.bigbasket.com/pd/10000159/fresho-potato-1-kg/", wait_until="networkidle")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
