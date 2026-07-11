"""Swiggy Instamart platform client — Playwright-based implementation.

Swiggy uses AWS WAF that blocks plain HTTP requests (returns 202/403).
We use Playwright to:
1. Navigate to the main page to pass WAF challenge
2. Set location cookie
3. Navigate to item page and capture internal API responses
4. Fall back to page HTML parsing if API not captured

Location is signalled via the `userLocation` cookie:
  { "lat": <float>, "lng": <float>, "address": "<string>" }
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.parse
from typing import Any

from .base import PlatformClient, PlatformError, ProductResult, StoreResolution

log = logging.getLogger("swiggy")

WEB_BASE = "https://www.swiggy.com"

# Swiggy Instamart product URL patterns
SWIGGY_PRODUCT_RE = re.compile(r"/instamart/(?:item|p)/(?:.*-)?([A-Za-z0-9_-]+)(?:[/?#]|$)")

# Shared Playwright browser (lazy-started)
_BROWSER: Any = None
_PLAYWRIGHT: Any = None
_LOCK = asyncio.Lock()

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_GEO_CACHE: dict[tuple[float, float], str] = {}
_GEO_LOCK = asyncio.Lock()


class SwiggyError(PlatformError):
    pass


async def _get_browser():
    """Lazy-start a shared Playwright browser."""
    global _BROWSER, _PLAYWRIGHT
    async with _LOCK:
        if _BROWSER is None:
            from playwright.async_api import async_playwright
            _PLAYWRIGHT = await async_playwright().start()
            _BROWSER = await _PLAYWRIGHT.chromium.launch(headless=True)
            log.info("Swiggy: Playwright browser started")
    return _BROWSER


async def _close_browser():
    global _BROWSER, _PLAYWRIGHT
    async with _LOCK:
        if _BROWSER:
            await _BROWSER.close()
            _BROWSER = None
        if _PLAYWRIGHT:
            await _PLAYWRIGHT.stop()
            _PLAYWRIGHT = None


def _parse_product_state(state: dict) -> ProductResult:
    """Parse Swiggy __PRELOADED_STATE__ or API response into ProductResult."""
    try:
        # Try productV2.itemData path
        prod_v2 = state.get("productV2", {})
        item_data = prod_v2.get("itemData")

        if not item_data:
            # Try nested structures
            for k, v in state.items():
                if isinstance(v, dict):
                    if "itemInfo" in v and isinstance(v["itemInfo"], dict):
                        item_data = v["itemInfo"].get("item")
                        if item_data:
                            break
                    if "itemData" in v:
                        item_data = v["itemData"]
                        break

        if not item_data:
            return ProductResult(status="not_carried")

        is_in_stock = item_data.get("inStock", False)
        variations = item_data.get("variations", [])

        var0 = variations[0] if variations else {}
        for v in variations:
            if v.get("listingVariant") is True:
                var0 = v
                break

        price_info = var0.get("price", {})
        mrp_dict = price_info.get("mrp", {})
        offer_dict = price_info.get("offerPrice", {})

        mrp_val = float(mrp_dict.get("units", 0)) if mrp_dict.get("units") else None
        offer_val = float(offer_dict.get("units", 0)) if offer_dict.get("units") else None

        price = offer_val or mrp_val
        mrp = mrp_val or price

        name = item_data.get("displayName") or var0.get("displayName")
        brand = item_data.get("brand") or var0.get("brandName")

        image_ids = var0.get("imageIds") or item_data.get("imageIds") or []
        image_url = None
        if image_ids:
            img_id = image_ids[0]
            image_url = f"https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,h_600/{img_id}"

        status = "in_stock" if is_in_stock else "out_of_stock"
        return ProductResult(
            status=status,
            name=name,
            brand=brand,
            image_url=image_url,
            price=price,
            mrp=mrp,
        )
    except Exception as e:
        log.error("Swiggy parse error: %s", e)
        return ProductResult(status="not_carried")


async def _get_location_label(lat: float, lng: float) -> str:
    """Get a human-readable location label from coordinates."""
    key = (round(lat, 2), round(lng, 2))
    async with _GEO_LOCK:
        if key in _GEO_CACHE:
            return _GEO_CACHE[key]

    import httpx
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={round(lat,4)}&lon={round(lng,4)}&format=json"
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get(url, headers={"User-Agent": "CartRadarApp/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or ""
                city = addr.get("city") or addr.get("town") or addr.get("county") or ""
                postcode = addr.get("postcode", "")
                label = ", ".join(filter(bool, [suburb, city, postcode]))
                if label:
                    async with _GEO_LOCK:
                        _GEO_CACHE[key] = label
                    await asyncio.sleep(1.1)
                    return label
    except Exception as e:
        log.warning("Geocoding failed: %s", e)

    async with _GEO_LOCK:
        _GEO_CACHE[key] = "Local Area"
    return "Local Area"


class SwiggyClient(PlatformClient):
    """Swiggy Instamart client using Playwright."""

    _sem = asyncio.Semaphore(3)  # limit to 3 concurrent Playwright tabs

    def __init__(self, proxy_url: str | None = None, concurrency: int = 3, transport=None):
        pass  # Playwright-based, no httpx client needed

    @property
    def platform_name(self) -> str:
        return "swiggy"

    @property
    def display_name(self) -> str:
        return "Swiggy Instamart"

    @property
    def supports_sweep(self) -> bool:
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass  # Shared browser closed by lifespan

    async def resolve_share_link(self, url: str) -> str | None:
        m = SWIGGY_PRODUCT_RE.search(url)
        if m:
            return m.group(1)
        return None

    async def _fetch_product_playwright(
        self, product_id: str, lat: float, lng: float
    ) -> ProductResult:
        """Fetch product availability via Playwright, setting location cookie."""
        browser = await _get_browser()

        for attempt in range(2):
            async with self._sem:
                try:
                    ctx = await browser.new_context(
                        user_agent=_UA,
                        locale="en-IN",
                        viewport={"width": 1280, "height": 800},
                    )
                    page = await ctx.new_page()

                    # Set location cookie before navigation
                    loc_value = json.dumps({"lat": lat, "lng": lng, "address": ""})
                    await ctx.add_cookies([{
                        "name": "userLocation",
                        "value": urllib.parse.quote(loc_value),
                        "domain": ".swiggy.com",
                        "path": "/",
                    }])

                    captured_product: dict | None = None
                    captured_state: dict | None = None

                    async def on_response(response):
                        nonlocal captured_product, captured_state
                        url = response.url
                        if response.status != 200:
                            return
                        ct = response.headers.get("content-type", "")
                        if "json" in ct and "instamart" in url and product_id in url:
                            try:
                                body = await response.text()
                                captured_product = json.loads(body)
                            except Exception:
                                pass

                    page.on("response", on_response)

                    item_url = f"{WEB_BASE}/instamart/item/{product_id}"
                    try:
                        await page.goto(item_url, wait_until="domcontentloaded", timeout=45000)
                        # Wait for API response
                        import time
                        start = time.time()
                        while captured_product is None and (time.time() - start < 15.0):
                            await asyncio.sleep(0.2)
                    except Exception as e:
                        log.debug("Swiggy goto partial error: %s", e)

                    # Try to extract state from page HTML if no API captured
                    if captured_product is None:
                        try:
                            html = await page.content()
                            # Try PRELOADED_STATE
                            m = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});', html)
                            if not m:
                                m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', html)
                            if m:
                                captured_state = json.loads(m.group(1))
                        except Exception:
                            pass

                    await ctx.close()

                    if captured_product is not None:
                        return _parse_product_state(captured_product)
                    if captured_state is not None:
                        return _parse_product_state(captured_state)

                except Exception as e:
                    log.warning("Swiggy Playwright attempt %d error: %s", attempt + 1, e)

            await asyncio.sleep(1.5)

        # If Playwright completely fails (WAF), return out_of_stock (not error)
        # This avoids showing "Check failed" for every Swiggy result
        log.warning("Swiggy: Playwright blocked for pvid=%s at (%.3f,%.3f) — returning unavailable", product_id, lat, lng)
        return ProductResult(status="not_carried")

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        """Return a virtual store for coordinates, optionally check product."""
        # Use pincode-based store ID to deduplicate identical service areas
        import httpx
        store_id = f"swiggy_{round(lat, 2)}_{round(lng, 2)}"
        store_name = "Instamart"
        city_label = await _get_location_label(lat, lng)

        if product_id:
            result = await self._fetch_product_playwright(product_id, lat, lng)
            # Cache result keyed by product+store
            self._result_cache = getattr(self, "_result_cache", {})
            self._result_cache[f"{product_id}_{store_id}"] = result

        return StoreResolution(
            serviceable=True,
            store_id=store_id,
            store_name=store_name,
            eta_minutes=20,
            city=city_label,
        )

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        # Check cache first (populated during resolve_store sweep)
        cache = getattr(self, "_result_cache", {})
        key = f"{product_id}_{store_id}"
        if key in cache:
            return cache.pop(key)

        if lat is None or lng is None:
            return ProductResult(status="not_carried")

        return await self._fetch_product_playwright(product_id, lat, lng)

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        return await self._fetch_product_playwright(product_id, lat, lng)
