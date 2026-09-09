"""
ZEPTO RESEARCH - Method 1: Raw httpx + BFF API (Current Approach)
Test product: Real Zepto pvid from a prior-working product URL
Test location: New Delhi (28.6139, 77.2090) - major Zepto market
"""
import asyncio, json, time, httpx
from urllib.parse import quote, unquote

WEB_BASE = "https://www.zepto.com"
BFF_BASE = "https://bff-gateway.zepto.com"
APP_VERSION = "16.2.11"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
SAMPLE_STORE_ID = "0059ff6a-7eb0-477a-a7f5-69256f2c444b"
TEST_PVID = "dce2c2e5-be28-4f1d-aced-e3b6b0d43e8a"
TEST_LAT, TEST_LNG = 28.6139, 77.2090
results = {}

async def main():
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0), follow_redirects=True,
        headers={"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"},
    ) as c:
        print("=" * 60)
        print("METHOD 1: Raw httpx + BFF API (current implementation)")
        print("=" * 60)

        # Step 1: handshake
        print("\n[Step 1] HEAD handshake www.zepto.com")
        t0 = time.time()
        try:
            r = await c.request("HEAD", WEB_BASE + "/", headers={"Accept": "text/html"})
            print(f"  HTTP {r.status_code} in {time.time()-t0:.2f}s")
            print(f"  Cookies: {list(c.cookies.keys())}")
            sid = c.cookies.get("session_id")
            xsrf = c.cookies.get("XSRF-TOKEN")
            print(f"  session_id present: {bool(sid)}")
            print(f"  XSRF-TOKEN present: {bool(xsrf)}")
            results["step1_http"] = r.status_code
            results["got_session"] = bool(sid)
        except Exception as e:
            print(f"  FAIL: {e}")
            results["step1_error"] = str(e); return

        if r.status_code != 200:
            print(f"\n  BLOCKED (HTTP {r.status_code}) - cannot proceed")
            results["blocked"] = True; return

        bff_hdrs = {
            "Accept": "application/json", "platform": "WEB", "tenant": "ZEPTO",
            "x-without-bearer": "true", "app_version": APP_VERSION,
            "Origin": WEB_BASE, "Referer": WEB_BASE + "/",
        }
        if xsrf:
            bff_hdrs["x-xsrf-token"] = unquote(xsrf)

        # Step 2: serviceability probe
        print(f"\n[Step 2] Serviceability probe ({TEST_LAT}, {TEST_LNG})")
        pos = quote(json.dumps({"latitude": TEST_LAT, "longitude": TEST_LNG}, separators=(",", ":")), safe="")
        t0 = time.time()
        store_id = SAMPLE_STORE_ID
        try:
            r2 = await c.request("HEAD", WEB_BASE + "/", headers={"Accept": "text/html", "Cookie": f"user_position={pos}"})
            print(f"  HTTP {r2.status_code} in {time.time()-t0:.2f}s")
            for sc in r2.headers.get_list("set-cookie"):
                if sc.startswith("serviceability="):
                    data = json.loads(unquote(sc.split(";",1)[0].split("=",1)[1]))
                    p = data.get("primaryStore") or {}
                    info = data.get("storeDetailedInfo") or {}
                    print(f"  serviceable={p.get('serviceable')} store_id={p.get('storeId')} city={info.get('city')} eta={p.get('etaInMinutes')}min")
                    results["serviceable"] = p.get("serviceable")
                    results["store_id"] = p.get("storeId")
                    results["store_name"] = info.get("name")
                    results["city"] = info.get("city")
                    if p.get("storeId"):
                        store_id = p["storeId"]
                    break
            else:
                print("  No serviceability cookie!")
                results["serviceable"] = None
        except Exception as e:
            print(f"  FAIL: {e}")
            results["step2_error"] = str(e)

        print(f"  Using store_id: {store_id} ({'SAMPLE' if store_id==SAMPLE_STORE_ID else 'REAL'})")
        results["using_sample_store"] = store_id == SAMPLE_STORE_ID

        # Step 3: product detail
        print(f"\n[Step 3] Product detail API (pvid={TEST_PVID})")
        t0 = time.time()
        try:
            r3 = await c.get(
                f"{BFF_BASE}/product-assortment-service/api/v2/product-detail",
                params={"storeId": store_id, "productVariantId": TEST_PVID},
                headers={**bff_hdrs, "storeId": store_id},
            )
            print(f"  HTTP {r3.status_code} in {time.time()-t0:.2f}s")
            results["product_http"] = r3.status_code
            if r3.status_code == 200:
                d = r3.json()
                prod = d.get("product") or {}
                sps = prod.get("storeProducts") or []
                fallback = d.get("fallbackType", "NONE")
                print(f"  product.name={prod.get('name')} brand={prod.get('brand')} fallback={fallback}")
                print(f"  storeProducts count={len(sps)}")
                if sps:
                    sp = sps[0]
                    oos = sp.get("outOfStock")
                    price = sp.get("discountedSellingPrice")
                    mrp = sp.get("mrp")
                    qty = sp.get("availableQuantity")
                    status = "out_of_stock" if oos else "in_stock"
                    print(f"  STATUS={status} price=Rs{price/100 if price else 'N/A'} mrp=Rs{mrp/100 if mrp else 'N/A'} qty={qty}")
                    results["status"] = status
                    results["price"] = price/100 if price else None
                    results["mrp"] = mrp/100 if mrp else None
                    results["genuine_data"] = True
                else:
                    print(f"  No storeProducts (fallback={fallback})")
                    results["status"] = f"not_listed (fallback={fallback})"
                    results["genuine_data"] = False
            else:
                print(f"  Body: {r3.text[:300]}")
                results["genuine_data"] = False
        except Exception as e:
            print(f"  FAIL: {e}")
            results["product_error"] = str(e)
            results["genuine_data"] = False

    print("\n" + "=" * 60)
    print("RESULTS JSON:")
    print(json.dumps(results, indent=2, default=str))

asyncio.run(main())
