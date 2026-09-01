"""Flipkart & Flipkart Minutes platform clients.

Normal Flipkart:
  Uses Playwright to fetch the product page and extracts price from application/ld+json.
  No location is required for standard Flipkart availability.

Flipkart Minutes:
  Requires location. Uses GPS injection via Playwright browser geolocation:

  1. Set browser geolocation to the user's lat/lng coordinates.
  2. Navigate to the HYPERLOCAL product URL.
  3. If Flipkart shows the address selection bottom sheet, click "Use my current location".
  4. Wait for the browser URL to change away from the hyperlocal-preview-page using
     wait_for_url() with a proper timeout — NOT a fixed sleep.
  5. If the URL is now the product page, wait for content to render, then extract price
     from both application/ld+json AND DOM scraping fallback.
  6. If the URL is still the preview page, try typing a Nominatim-resolved pincode into
     the search box (same approach as BigBasket: lat/lng → Nominatim → pincode → input).

  Key findings from empirical testing (2026-09-01):
  - GPS injection (lat=25.6012, lng=85.0697 for Dhanaut/Patna) works correctly.
  - After click, Flipkart navigates FROM hyperlocal-preview-page TO the actual product page.
  - The URL change signals serviceability; no change signals unserviceable area.
  - wait_for_url() is essential — a fixed 4s sleep is insufficient.
  - ld+json on Flipkart Minutes product page does NOT always contain price;
    DOM-based price extraction is needed as fallback.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx

from .base import PlatformClient, ProductResult, StoreResolution
from .blinkit import _get_browser

log = logging.getLogger("flipkart")

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Extracts product data from ld+json
_LD_JSON_JS = '''() => {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of scripts) {
        try {
            const data = JSON.parse(script.textContent);
            let items = Array.isArray(data) ? data : [data];
            for (const item of items) {
                if (item["@type"] === "Product" && item.offers && item.offers.price) {
                    return {
                        price: parseFloat(item.offers.price),
                        name: item.name || null,
                        brand: (item.brand && item.brand.name) || null,
                        image: (typeof item.image === "string") ? item.image
                               : (Array.isArray(item.image) ? item.image[0] : null),
                    };
                }
            }
        } catch (e) {}
    }
    return null;
}'''

# Flipkart Minutes product pages have NO ld+json — price is in the React DOM.
# Empirically verified class names (2026-09-01):
#   v1zwn20  → MRP (struck-through original price); first ₹xxx text node
#   v1zwn22  → Discounted selling price; first ₹xxx text node
# Both classes contain multiple children; we must find the first text node
# that starts with ₹ and contains only a number.
_DOM_PRICE_JS = r'''() => {
    function extractPrice(sel) {
        // Walk text nodes inside matching elements to find the ₹ price
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
        let node;
        while ((node = walker.nextNode())) {
            const t = node.textContent.trim();
            if (/^₹\d/.test(t)) {
                // Check if this text node's ancestor matches our selector
                let el = node.parentElement;
                for (let i = 0; i < 4; i++) {
                    if (!el) break;
                    if (el.matches(sel)) {
                        const num = parseFloat(t.replace(/[^\d.]/g, ""));
                        if (!isNaN(num) && num > 0 && num < 500000) return num;
                    }
                    el = el.parentElement;
                }
            }
        }
        return null;
    }

    // selling price first (v1zwn22), then MRP (v1zwn20)
    const selling = extractPrice("div.v1zwn22");
    if (selling) return selling;
    const mrp = extractPrice("div.v1zwn20");
    if (mrp) return mrp;

    // Standard Flipkart (non-Minutes) fallback
    for (const sel of ["div.Nx9bqj", "div[class*='_30jeq3']"]) {
        const el = document.querySelector(sel);
        if (el) {
            const num = parseFloat(el.textContent.replace(/[^\d.]/g, ""));
            if (!isNaN(num) && num > 0) return num;
        }
    }
    return null;
}'''

_UNSERVICEABLE_SLUGS = ("flipkart-minutes-store", "hyperlocal-preview-page")


def _is_unserviceable(url: str) -> bool:
    return any(slug in url for slug in _UNSERVICEABLE_SLUGS)


async def _reverse_geocode_pincode(lat: float, lng: float) -> str | None:
    """Return the postal code for a lat/lng pair via Nominatim (no API key needed)."""
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={round(lat, 5)}&lon={round(lng, 5)}&format=json&addressdetails=1"
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            resp = await c.get(url, headers={"User-Agent": "CartRadarApp/1.0"})
            if resp.status_code == 200:
                return resp.json().get("address", {}).get("postcode") or None
    except Exception as e:
        log.warning("Flipkart: Nominatim reverse-geocode failed: %s", e)
    return None


async def _extract_product_result(page) -> ProductResult:
    """Extract price from ld+json, then fallback to DOM scraping.
    
    Flipkart Minutes product pages have NO ld+json — price is React-rendered.
    We wait 5s for the DOM to fully render before scraping.
    """
    # Flipkart Minutes React renders the price asynchronously; give it time
    await page.wait_for_timeout(5000)

    result = await page.evaluate(_LD_JSON_JS)
    if result and result.get("price"):
        log.info("Flipkart: price extracted from ld+json: %s", result["price"])
        return ProductResult(
            status="in_stock",
            price=result["price"],
            mrp=result["price"],
            name=result.get("name"),
            brand=result.get("brand"),
            image_url=result.get("image"),
        )

    # ld+json missing or no price — try DOM (Flipkart Minutes product pages)
    dom_price = await page.evaluate(_DOM_PRICE_JS)
    if dom_price:
        # Also extract MRP (v1zwn20) separately
        dom_mrp = await page.evaluate(r'''() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
            let node;
            while ((node = walker.nextNode())) {
                const t = node.textContent.trim();
                if (/^₹\d/.test(t)) {
                    let el = node.parentElement;
                    for (let i = 0; i < 4; i++) {
                        if (!el) break;
                        if (el.matches("div.v1zwn20")) {
                            const num = parseFloat(t.replace(/[^\d.]/g, ""));
                            if (!isNaN(num) && num > 0 && num < 500000) return num;
                        }
                        el = el.parentElement;
                    }
                }
            }
            return null;
        }''')
        log.info("Flipkart: price=%s mrp=%s (DOM)", dom_price, dom_mrp)
        return ProductResult(status="in_stock", price=dom_price, mrp=dom_mrp or dom_price)

    log.warning("Flipkart: on product page but price not found — returning out_of_stock")
    return ProductResult(status="out_of_stock")


# ──────────────────────────────────────────────────────────────────────────────
# Normal Flipkart
# ──────────────────────────────────────────────────────────────────────────────

class FlipkartClient(PlatformClient):
    """Standard Flipkart platform client (non-Minutes)."""

    @property
    def platform_name(self) -> str:
        return "flipkart"

    @property
    def display_name(self) -> str:
        return "Flipkart"

    @property
    def supports_sweep(self) -> bool:
        return False

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        return None

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        """Fetch price from normal Flipkart. Location not required for stock status."""
        browser = await _get_browser()
        context = await browser.new_context(user_agent=_UA)
        page = await context.new_page()
        url = f"https://www.flipkart.com/product/p/itme?pid={product_id}&marketplace=FLIPKART"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            result = await page.evaluate(_LD_JSON_JS)
            if result and result.get("price"):
                return ProductResult(
                    status="in_stock",
                    price=result["price"],
                    mrp=result["price"],
                    name=result.get("name"),
                    brand=result.get("brand"),
                    image_url=result.get("image"),
                )
            return ProductResult(status="not_carried")
        except Exception as e:
            log.warning("Flipkart normal extraction failed: %s", e)
            return ProductResult(status="error")
        finally:
            await context.close()

    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        return StoreResolution(serviceable=False)

    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        return ProductResult(status="error")


# ──────────────────────────────────────────────────────────────────────────────
# Flipkart Minutes
# ──────────────────────────────────────────────────────────────────────────────

class FlipkartMinutesClient(PlatformClient):
    """Flipkart Minutes (HYPERLOCAL) platform client.

    Proven working strategy (empirically verified 2026-09-01):
    1. Inject geolocation (lat/lng) into a headless Chromium context.
    2. Navigate to the product URL with marketplace=HYPERLOCAL.
    3. Click "Use my current location" on the address selection page.
    4. Use wait_for_url() to wait for URL to change — this is the key fix.
       A URL change from hyperlocal-preview-page → product URL means SERVICEABLE.
       No URL change means UNSERVICEABLE.
    5. Extract price from ld+json or DOM fallback.

    Fallback: if GPS step fails, reverse-geocode lat/lng to a pincode via Nominatim
    and type it into the address search input on the preview page.
    """

    def __init__(self):
        super().__init__()
        # Cache for product results fetched during resolve_store
        self._result_cache: dict[str, ProductResult] = {}
        # Concurrency limit to prevent OOM
        self._sem = asyncio.Semaphore(2)

    @property
    def platform_name(self) -> str:
        return "flipkart_minutes"

    @property
    def display_name(self) -> str:
        return "Flipkart Minutes"

    @property
    def supports_sweep(self) -> bool:
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        return None

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        if not product_id:
            return StoreResolution(serviceable=False)
            
        store_id = f"fm_coverage_{round(lat, 3)}_{round(lng, 3)}"

        # If we already resolved and cached this, skip
        if f"{product_id}_{store_id}" in self._result_cache:
            return StoreResolution(
                serviceable=True,
                store_id=store_id,
                store_name="Flipkart Minutes Coverage Area",
                eta_minutes=None,
                city=None,
            )

        browser = await _get_browser()
        product_url = f"https://www.flipkart.com/product/p/itme?pid={product_id}&marketplace=HYPERLOCAL"

        async with self._sem:
            # ── Strategy 1: GPS injection + wait_for_url navigation ───────────────
            ctx = await browser.new_context(
                user_agent=_UA,
                geolocation={"longitude": lng, "latitude": lat},
                permissions=["geolocation"],
            )
            page = await ctx.new_page()
            try:
                await page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
                # The "Use my current location" button is rendered by React asynchronously
                await page.wait_for_timeout(4000)

                if not _is_unserviceable(page.url):
                    # Already on product page (location already set from a previous visit)
                    log.info("Flipkart Minutes: landed directly on product page: %s", page.url)
                    result = await _extract_product_result(page)
                    self._result_cache[f"{product_id}_{store_id}"] = result
                    return StoreResolution(
                        serviceable=True, store_id=store_id, store_name="Flipkart Minutes Coverage Area", city=None
                    )

                # On preview/address-selection page — click GPS button
                loc_btns = await page.locator("text=/Use my current location/i").all()
                if loc_btns:
                    log.info("Flipkart Minutes: clicking 'Use my current location'")
                    await loc_btns[0].click(timeout=5000)

                    # KEY FIX: wait_for_url() until we leave the preview page
                    try:
                        await page.wait_for_url(
                            lambda url: not _is_unserviceable(url),
                            timeout=12000,
                        )
                        log.info("Flipkart Minutes: URL changed to product page — SERVICEABLE")
                        result = await _extract_product_result(page)
                        self._result_cache[f"{product_id}_{store_id}"] = result
                        return StoreResolution(
                            serviceable=True, store_id=store_id, store_name="Flipkart Minutes Coverage Area", city=None
                        )
                    except Exception:
                        log.info("Flipkart Minutes: GPS location not accepted — still on preview page")

                # ── Strategy 2: Pincode entry fallback ────────────────────────────
                pincode = await _reverse_geocode_pincode(lat, lng)
                log.info("Flipkart Minutes: trying pincode fallback, pincode=%s", pincode)

                if pincode:
                    inp_sel = "input[placeholder*='Search'], input[placeholder*='area'], input[placeholder*='pin code'], input[placeholder*='pincode']"
                    inputs = await page.locator(inp_sel).all()

                    for inp in inputs:
                        try:
                            await inp.click()
                            await inp.fill(pincode)
                            await page.wait_for_timeout(2000)

                            suggestions = await page.locator(
                                "li[role='option'], [class*='Suggestion'], [class*='suggestion'], [class*='listItem']"
                            ).all()
                            
                            if suggestions:
                                await suggestions[0].click(timeout=5000)
                            else:
                                await inp.press("Enter")

                            try:
                                await page.wait_for_url(
                                    lambda url: not _is_unserviceable(url),
                                    timeout=10000,
                                )
                                log.info("Flipkart Minutes: pincode strategy navigated to product page")
                                result = await _extract_product_result(page)
                                self._result_cache[f"{product_id}_{store_id}"] = result
                                return StoreResolution(
                                    serviceable=True, store_id=store_id, store_name="Flipkart Minutes Coverage Area", city=None
                                )
                            except Exception:
                                log.info("Flipkart Minutes: pincode strategy also unserviceable")
                            break
                        except Exception as e:
                            log.debug("Flipkart Minutes: pincode input error: %s", e)

                # Both strategies failed — genuinely unserviceable
                return StoreResolution(serviceable=False)

            except Exception as e:
                log.warning("Flipkart Minutes extraction failed: %s", e)
                raise PlatformError(f"Flipkart Minutes error: {e}")
            finally:
                await ctx.close()

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        key = f"{product_id}_{store_id}"
        if key in self._result_cache:
            return self._result_cache.pop(key)
        
        # If not cached, we must resolve it again.
        if lat is not None and lng is not None:
            res = await self.resolve_store(lat, lng, product_id)
            if res.serviceable and res.store_id == store_id:
                return self._result_cache.pop(key, ProductResult(status="error"))
            
        return ProductResult(status="not_carried")

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        store = await self.resolve_store(lat, lng, product_id=product_id)
        if not store.serviceable or not store.store_id:
            return ProductResult(status="not_carried")
        return await self.product_at_store(product_id, store.store_id, lat=lat, lng=lng)
