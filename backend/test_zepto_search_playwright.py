import asyncio
from playwright.async_api import async_playwright

async def get_real_product():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle", timeout=20000)
        
        # Wait for the page to load
        await page.wait_for_timeout(3000)
        
        # Search for something common
        search_url = "https://bff-gateway.zepto.com/product-assortment-service/api/v1/search?query=milk&pageNumber=0&mode=AUTOSUGGEST"
        api_resp = await context.request.get(
            search_url,
            headers={
                "platform": "WEB",
                "tenant": "ZEPTO",
                "app_version": "16.2.11"
            }
        )
        
        if api_resp.status == 200:
            data = await api_resp.json()
            # print(json.dumps(data, indent=2))
            # Just extract the first product Variant ID
            try:
                products = data["layout"][0]["widget"]["data"]["searchResult"]["products"]
                if products:
                    first_pvid = products[0]["productVariant"]["id"]
                    first_name = products[0]["product"]["name"]
                    print(f"Found product: {first_name} (PVID: {first_pvid})")
            except Exception as e:
                print(f"Error parsing search result: {e}")
                print(await api_resp.text())
        else:
            print(f"Search API failed: {api_resp.status} - {await api_resp.text()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_real_product())
