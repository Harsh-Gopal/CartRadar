import asyncio
from playwright.async_api import async_playwright

async def run_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print("Navigating to Zepto to clear WAF...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        
        lat, lng = 30.7415, 76.6521
        print(f"\nRequesting get_page for {lat}, {lng} directly via context.request...")
        resp = await context.request.get(
            f"https://bff-gateway.zepto.com/lms/api/v2/get_page?latitude={lat}&longitude={lng}&page_type=HOME&version=v2&show_new_eta_banner=true&page_size=3&enforce_platform_type=DESKTOP",
            headers={"platform": "WEB", "tenant": "ZEPTO", "app_version": "16.2.11"}
        )
        
        print(f"Status: {resp.status}")
        try:
            data = await resp.json()
            serviceability = data.get("storeServiceableResponse", {})
            print(f"Serviceable: {serviceability.get('serviceable')}")
            print(f"Store ID: {serviceability.get('storeId')}")
            print(f"Secondary Store IDs: {serviceability.get('secondaryStoreIds')}")
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_trace())
