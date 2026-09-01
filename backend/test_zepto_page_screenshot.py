import asyncio
from app.platforms.zepto.client import ZeptoPlaywrightSession

async def main():
    pvid = "e6417757-5503-490f-90e0-c3d5ffcb3a70"
    url = f"https://www.zeptonow.com/pn/product/pvid/{pvid}"
    
    async with ZeptoPlaywrightSession() as session:
        await session.probe_location(28.6083, 77.2987)
        page = session.page
        await page.goto(url, wait_until="networkidle")
        await page.screenshot(path="zepto_product_page.png")
        print("Screenshot saved.")

if __name__ == "__main__":
    asyncio.run(main())
