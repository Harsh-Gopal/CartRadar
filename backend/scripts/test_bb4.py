import asyncio
import json
import re
from app.platforms.bigbasket import BigBasketClient

async def main():
    client = BigBasketClient()
    resp = await client._fetch_product_page("241602", 28.6273928, 77.1716954)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
    if m:
        state = json.loads(m.group(1))
        f = open("tmp_bb_state.json", "w")
        f.write(json.dumps(state, indent=2))
        f.close()
        print("Wrote state to tmp_bb_state.json")
    else:
        print("Not found", resp.status_code)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
