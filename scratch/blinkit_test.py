import httpx
import re
import json

url = "https://blinkit.com/pr/tata-tea-gold/prid/10532"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}
cookies = {"lat_long": "12.9716,77.5946"}
resp = httpx.get(url, headers=headers, cookies=cookies, follow_redirects=True)
print("Status:", resp.status_code)
if resp.status_code != 200:
    print("Headers:", resp.headers)
    print("Snippet:", resp.text[:200])

match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});', resp.text)
if not match:
    match = re.search(r'window\.grofers\s*=\s*(\{.*?\});', resp.text)

if match:
    j = json.loads(match.group(1))
    print("Found JSON")
    # print sample of product
    try:
        bff = j["PRELOADED_STATE"]["ui"]["pdp"]["bffPdp"]["bffData"]
        p = bff.get("product")
        if p:
            print("Product name:", p.get("name"))
            print("Product price:", p.get("price"))
            print("Product mrp:", p.get("mrp"))
            print("Product image:", p.get("image_url"))
            print("Product id:", p.get("product_id") or p.get("id"))
    except:
        pass
else:
    print("No JSON found")
