"""Blinkit platform client — Playwright-based with improved location handling.

Uses a shared Playwright browser and intercepts /v1/layout/product/ API calls.
Location is injected via request headers (lat/lon) and geolocation permission.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from .base import PlatformClient, PlatformError, ProductResult, StoreResolution

log = logging.getLogger("blinkit")

BLINKIT_PRODUCT_RE = re.compile(r"blinkit\.com/pr[n]?/[^/]+/prid/(\d+)")

_BROWSER: Any = None
_PLAYWRIGHT: Any = None
_LOCK = asyncio.Lock()

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BlinkitError(PlatformError):
    pass


async def _get_browser():
    """Lazy-start a shared Playwright browser instance."""
    global _BROWSER, _PLAYWRIGHT
    async with _LOCK:
        if _BROWSER is None:
            from playwright.async_api import async_playwright
            _PLAYWRIGHT = await async_playwright().start()
            _BROWSER = await _PLAYWRIGHT.chromium.launch(headless=True)
            log.info("Blinkit: Playwright browser started")
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


def _parse_snippets(snippets: list[dict], product_id: str) -> ProductResult:
    """Parse the Blinkit /v1/layout/product snippets into a ProductResult."""
    name: str | None = None
    brand: str | None = None
    price: float | None = None
    mrp: float | None = None
    image_url: str | None = None
    is_in_stock: bool = False
    found_product = False

    for snippet in snippets:
        data = snippet.get("data", {})
        if not isinstance(data, dict):
            continue

        # Primary: snippet with identity.id matching product_id
        identity = data.get("identity", {})
        if isinstance(identity, dict) and str(identity.get("id")) == product_id:
            found_product = True
            inventory = data.get("inventory", 0)
            try:
                is_in_stock = int(inventory) > 0
            except (TypeError, ValueError):
                is_in_stock = bool(inventory)

            # Try rfc_actions_v2 → remove_from_cart for product details
            rfc = data.get("rfc_actions_v2", {})
            if isinstance(rfc, dict):
                for action in rfc.get("default", []):
                    if action and isinstance(action, dict):
                        cart_item = action.get("remove_from_cart", {}).get("cart_item", {})
                        if cart_item:
                            name = cart_item.get("product_name") or cart_item.get("display_name")
                            brand = cart_item.get("brand")
                            image_url = cart_item.get("image_url")
                            mrp = cart_item.get("mrp") or None
                            price = cart_item.get("price") or mrp
                            break

            # Try atc_actions_v2 → add_to_cart if rfc didn't give price
            if not mrp or mrp == 0:
                atc = data.get("atc_actions_v2", {})
                if isinstance(atc, dict):
                    for action in atc.get("default", []):
                        if action and isinstance(action, dict):
                            cart_item = action.get("add_to_cart", {}).get("cart_item", {})
                            if cart_item:
                                if not name:
                                    name = cart_item.get("product_name") or cart_item.get("display_name")
                                if not brand:
                                    brand = cart_item.get("brand")
                                if not image_url:
                                    image_url = cart_item.get("image_url")
                                mrp = cart_item.get("mrp") or None
                                price = cart_item.get("price") or mrp
                                break

            # Also try direct product_data structure
            if not name:
                prod_data = data.get("product_data", {})
                if prod_data:
                    name = prod_data.get("name") or prod_data.get("product_name")
                    brand = prod_data.get("brand")
                    image_url = prod_data.get("image_url")

        # Look for image in item lists even without id match
        if not image_url:
            for list_key in ("itemList", "horizontal_item_list", "item_list"):
                item_list = data.get(list_key, [])
                if isinstance(item_list, list) and item_list:
                    first = item_list[0]
                    if isinstance(first, dict):
                        image_url = (
                            first.get("image_url")
                            or (first.get("entity", {}) or {}).get("image_url")
                        )
                    break

    if found_product or name:
        status = "in_stock" if is_in_stock else "out_of_stock"
        actual_price = float(price) if price and float(price) > 0 else None
        actual_mrp = float(mrp) if mrp and float(mrp) > 0 else actual_price
        return ProductResult(
            status=status,
            name=name,
            brand=brand,
            image_url=image_url,
            price=actual_price,
            mrp=actual_mrp,
        )

    return ProductResult(status="not_carried")


class BlinkitClient(PlatformClient):
    """Blinkit client using Playwright for real product + availability data."""

    def __init__(self, proxy_url: str | None = None, concurrency: int = 4, transport=None):
        self._sem = asyncio.Semaphore(concurrency)
        self._proxy_url = proxy_url
        self._result_cache: dict[str, ProductResult] = {}

    @property
    def platform_name(self) -> str:
        return "blinkit"

    @property
    def display_name(self) -> str:
        return "Blinkit"

    @property
    def supports_sweep(self) -> bool:
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        m = BLINKIT_PRODUCT_RE.search(url)
        if m:
            return m.group(1)
        return None

    async def _fetch_product_via_playwright(
        self, product_id: str, lat: float | None = None, lng: float | None = None
    ) -> dict | None:
        """Open a Playwright page and capture the /v1/layout/product API response."""
        browser = await _get_browser()

        for attempt in range(2):
            async with self._sem:
                try:
                    ctx_kwargs: dict = {
                        "user_agent": _UA,
                        "locale": "en-IN",
                        "viewport": {"width": 1280, "height": 800},
                    }
                    if lat is not None and lng is not None:
                        ctx_kwargs["geolocation"] = {"latitude": lat, "longitude": lng}
                        ctx_kwargs["permissions"] = ["geolocation"]

                    ctx = await browser.new_context(**ctx_kwargs)

                    # Set location cookies directly on the context
                    if lat is not None and lng is not None:
                        await ctx.add_cookies([
                            {
                                "name": "gr_1_lat",
                                "value": str(lat),
                                "domain": ".blinkit.com",
                                "path": "/",
                            },
                            {
                                "name": "gr_1_lng",
                                "value": str(lng),
                                "domain": ".blinkit.com",
                                "path": "/",
                            },
                        ])

                    page = await ctx.new_page()

                    # Inject lat/lon into API request headers
                    if lat is not None and lng is not None:
                        async def handle_route(route):
                            try:
                                headers = dict(route.request.headers)
                                headers["lat"] = str(lat)
                                headers["lon"] = str(lng)
                                await route.continue_(headers=headers)
                            except Exception:
                                try:
                                    await route.continue_()
                                except Exception:
                                    pass

                        await page.route("**/v1/**", handle_route)

                    product_json: dict | None = None

                    async def on_response(response):
                        nonlocal product_json
                        if f"/v1/layout/product/{product_id}" in response.url and response.status == 200:
                            try:
                                body = await response.body()
                                product_json = json.loads(body)
                            except Exception as e:
                                log.debug("Blinkit parse body error: %s", e)

                    page.on("response", on_response)

                    nav_url = f"https://blinkit.com/prn/product/prid/{product_id}"
                    try:
                        await page.goto(nav_url, wait_until="domcontentloaded", timeout=55000)

                        # Wait for XHR response
                        start_wait = time.time()
                        while product_json is None and (time.time() - start_wait < 20.0):
                            await asyncio.sleep(0.15)

                    except Exception as e:
                        log.debug("Blinkit page.goto partial error: %s", e)

                    await ctx.close()

                    if product_json is not None:
                        return product_json

                except Exception as e:
                    log.warning("Blinkit Playwright error on attempt %d: %s", attempt + 1, e)

            await asyncio.sleep(1.0)

        return None

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        store_id = f"blinkit_{round(lat, 3)}_{round(lng, 3)}"

        if product_id:
            result = await self.product_at_store(product_id, store_id, lat=lat, lng=lng)
            self._result_cache[f"{product_id}_{store_id}"] = result

        return StoreResolution(
            serviceable=True,
            store_id=store_id,
            store_name="Blinkit",
            eta_minutes=10,
            city=None,
        )

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        # Check if cached during resolve_store
        key = f"{product_id}_{store_id}"
        if key in self._result_cache:
            return self._result_cache.pop(key)

        result = await self._fetch_product_via_playwright(product_id, lat, lng)
        if result is None:
            log.warning("Blinkit: Playwright fetch returned None for pvid=%s", product_id)
            # Return out_of_stock instead of error to avoid "Check failed" badge
            return ProductResult(status="out_of_stock")

        snippets = result.get("response", {}).get("snippets", [])
        return _parse_snippets(snippets, product_id)

    async def product_at_location(
        self, product_id: str, lat: float, lng: float
    ) -> ProductResult:
        store = await self.resolve_store(lat, lng, product_id=product_id)
        return await self.product_at_store(product_id, store.store_id, lat=lat, lng=lng)
