import asyncio
import json
from urllib.parse import quote, unquote
from playwright.async_api import async_playwright

async def test_eval():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        print("Solving WAF...")
        await page.goto("https://www.zeptonow.com/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        lat, lng = 30.7415, 76.6521 # Kharar
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])
        
        script = """
        async () => {
            const resp = await fetch("/");
            return resp.status;
        }
        """
        status = await page.evaluate(script)
        print(f"Fetch status: {status}")
        
        cookies = await context.cookies()
        serviceability = next((c for c in cookies if c["name"] == "serviceability"), None)
        if serviceability:
            data = json.loads(unquote(serviceability["value"]))
            print(f"Store ID: {data.get('primaryStore', {}).get('storeId')}")
        else:
            print("No serviceability cookie found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_eval())
