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
from ..normalization import parse_quantity

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
            try:
                from playwright.async_api import async_playwright
                _PLAYWRIGHT = await async_playwright().start()
                _BROWSER = await _PLAYWRIGHT.chromium.launch(headless=True)
                log.info("Blinkit: Playwright browser started successfully")
            except Exception as exc:
                log.error(
                    "Blinkit: Playwright browser FAILED to start: %s — "
                    "Blinkit searches will return errors. "
                    "Run 'playwright install-deps chromium' to fix missing system libraries.",
                    exc,
                )
                _PLAYWRIGHT = None
                _BROWSER = None
                raise BlinkitError(f"Playwright launch failed: {exc}") from exc
    return _BROWSER


async def prewarm_browser():
    """Pre-warm Playwright at startup so the first search isn't slow.
    
    Called from the FastAPI lifespan hook. Errors are logged but not raised
    so a broken Playwright doesn't prevent the whole server from starting.
    """
    try:
        await _get_browser()
        log.info("Blinkit: browser pre-warm complete")
    except Exception as exc:
        log.warning("Blinkit: browser pre-warm failed (Blinkit searches will be slow on first request): %s", exc)


async def _close_browser():
    global _BROWSER, _PLAYWRIGHT
    async with _LOCK:
        if _BROWSER:
            await _BROWSER.close()
            _BROWSER = None
        if _PLAYWRIGHT:
            await _PLAYWRIGHT.stop()
            _PLAYWRIGHT = None


def _parse_price_text(text: str | None) -> float | None:
    """Extract numeric price from Blinkit's text like '₹160' or '160'."""
    if not text:
        return None
    # Strip currency symbols and whitespace, keep digits and decimal point
    cleaned = re.sub(r"[^\d.]", "", str(text))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


def _parse_snippets(snippets: list[dict], product_id: str) -> ProductResult:
    """Parse the Blinkit /v1/layout/product snippets into a ProductResult.

    Stock detection strategy (in priority order):
    1. `inventory`, `is_sold_out`, `product_state` fields on the identity-matched
       snippet — these are the most direct and reliable signals in Blinkit's API.
       NOTE: The `widget` field is always None/absent in Blinkit's actual API
       responses; do NOT rely on widget-type filtering.
    2. `stepper_data.state.title.text == "enabled"` as a proxy for add-to-cart
       being available (= in stock).
    3. `tracking.common_attributes` for price, mrp, state, inventory.
    4. `rfc_actions_v2` / `atc_actions_v2` for product name, brand, image, price.

    Explicitly distinguishes:
    - `in_stock`: product is available for purchase at this location
    - `out_of_stock`: product is known to be unavailable (sold out)
    - `not_carried`: product not found in response (may not be sold at this store)
    - `error`: returned by the caller when Playwright itself fails
    """
    name: str | None = None
    brand: str | None = None
    price: float | None = None
    mrp: float | None = None
    image_url: str | None = None
    raw_quantity: str | None = None

    # Tri-state: None = not yet determined; True/False = explicitly known
    is_in_stock: bool | None = None
    found_product = False

    for snippet in snippets:
        data = snippet.get("data", {})
        if not data:
            continue

        # ── Match by product identity ─────────────────────────────────────────
        identity = data.get("identity", {})
        snippet_id = str(identity.get("id")) if isinstance(identity, dict) else None
        is_target = snippet_id == product_id

        if is_target:
            found_product = True

            # ── 1. Direct inventory / stock fields (most reliable) ────────────
            # These fields appear directly on the product card snippet.
            # `inventory` is an integer count (>0 = available).
            # `is_sold_out` is a boolean.
            # `product_state` is a string: "available" | "sold_out" | "unavailable"
            raw_inventory = data.get("inventory")
            is_sold_out = data.get("is_sold_out")
            product_state = data.get("product_state")

            if raw_inventory is not None:
                try:
                    inv = int(raw_inventory)
                    is_in_stock = inv > 0
                    log.debug("Blinkit[%s]: inventory=%d → is_in_stock=%s", product_id, inv, is_in_stock)
                except (TypeError, ValueError):
                    pass

            if is_in_stock is None and is_sold_out is not None:
                is_in_stock = not bool(is_sold_out)
                log.debug("Blinkit[%s]: is_sold_out=%s → is_in_stock=%s", product_id, is_sold_out, is_in_stock)

            if is_in_stock is None and product_state:
                is_in_stock = str(product_state).lower() == "available"
                log.debug("Blinkit[%s]: product_state=%r → is_in_stock=%s", product_id, product_state, is_in_stock)

            # ── 2. Stepper (Add to Cart button state) ────────────────────────
            # When is_in_stock is still None, check if the stepper is "enabled".
            # Blinkit disables/removes the stepper for OOS items.
            if is_in_stock is None:
                stepper = data.get("stepper_data", {})
                stepper_state = (
                    stepper.get("state", {}).get("title", {}).get("text", "") if stepper else ""
                )
                if stepper_state:
                    is_in_stock = stepper_state.lower() == "enabled"
                    log.debug("Blinkit[%s]: stepper_state=%r → is_in_stock=%s", product_id, stepper_state, is_in_stock)

            # ── 3. Price from normal_price.text ───────────────────────────────
            normal_price = data.get("normal_price", {})
            if isinstance(normal_price, dict):
                p = _parse_price_text(normal_price.get("text"))
                if p and not price:
                    price = p
                    if not mrp:
                        mrp = p

            # ── 4. Variant text from variant.text ─────────────────────────────
            variant_data = data.get("variant", {})
            if isinstance(variant_data, dict) and not raw_quantity:
                raw_quantity = variant_data.get("text")

            # ── 5. rfc_actions_v2 (remove-from-cart has full product details) ─
            rfc = data.get("rfc_actions_v2", {})
            if isinstance(rfc, dict):
                for action in rfc.get("default", []):
                    if action and isinstance(action, dict):
                        cart_item = action.get("remove_from_cart", {}).get("cart_item", {})
                        if cart_item:
                            if not name:
                                name = cart_item.get("product_name") or cart_item.get("display_name")
                            if not brand:
                                brand = cart_item.get("brand")
                            if not image_url:
                                image_url = cart_item.get("image_url")
                            if not raw_quantity:
                                raw_quantity = cart_item.get("unit") or cart_item.get("quantity")
                            ci_mrp = cart_item.get("mrp")
                            ci_price = cart_item.get("price")
                            if ci_mrp and not mrp:
                                mrp = ci_mrp
                            if ci_price and not price:
                                price = ci_price or mrp
                            break

            # ── 6. atc_actions_v2 (add-to-cart, when populated) ───────────────
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
                            if not raw_quantity:
                                raw_quantity = cart_item.get("unit") or cart_item.get("quantity")
                            ci_mrp = cart_item.get("mrp")
                            ci_price = cart_item.get("price")
                            if ci_mrp and not mrp:
                                mrp = ci_mrp
                            if ci_price and not price:
                                price = ci_price or mrp
                            break

        # ── 7. Tracking common_attributes (available on some snippets) ─────────
        # Even on non-identity snippets, tracking data may provide price/state.
        tracking = snippet.get("tracking", {})
        common_attrs = tracking.get("common_attributes", {}) if isinstance(tracking, dict) else {}
        if isinstance(common_attrs, dict) and str(common_attrs.get("product_id")) == product_id:
            if not name:
                # tracking rarely has the name, but try
                pass
            if not price:
                ta_price = common_attrs.get("price")
                if ta_price:
                    try:
                        price = float(ta_price)
                    except (TypeError, ValueError):
                        pass
            if not mrp:
                ta_mrp = common_attrs.get("mrp")
                if ta_mrp:
                    try:
                        mrp = float(ta_mrp)
                    except (TypeError, ValueError):
                        pass
            # Use tracking state if we still don't know stock status
            if is_in_stock is None:
                ta_state = common_attrs.get("state")
                if ta_state:
                    is_in_stock = str(ta_state).lower() == "available"
                    log.debug("Blinkit[%s]: tracking state=%r → is_in_stock=%s", product_id, ta_state, is_in_stock)
            # Extract name from title snippet if still missing
            if not name:
                data_for_title = snippet.get("data", {})
                title = data_for_title.get("title", {})
                if isinstance(title, dict):
                    name = title.get("text") or name

        # ── 8. Image from item lists ──────────────────────────────────────────
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

    if not found_product and not name:
        return ProductResult(status="not_carried")

    # ── Final stock resolution ───────────────────────────────────────────────
    if is_in_stock is None:
        # No explicit stock signal found — default out_of_stock when product was found
        # (but log it clearly so we know which signal path failed)
        log.warning(
            "Blinkit[%s]: product found but no stock signal detected "
            "(no inventory/is_sold_out/product_state/stepper). Defaulting to out_of_stock.",
            product_id,
        )
        is_in_stock = False

    status = "in_stock" if is_in_stock else "out_of_stock"
    actual_price = float(price) if price and float(price) > 0 else None
    actual_mrp = float(mrp) if mrp and float(mrp) > 0 else actual_price

    variant_label = raw_quantity if raw_quantity else (name or "")
    nq = parse_quantity(variant_label)

    return ProductResult(
        status=status,
        name=name,
        brand=brand,
        image_url=image_url,
        price=actual_price,
        mrp=actual_mrp,
        pack_count=nq.pack_count if nq else None,
        quantity_per_pack=nq.quantity_per_pack if nq else None,
        quantity_unit=nq.quantity_unit if nq else None,
        total_quantity=nq.total_quantity if nq else None,
        total_quantity_unit=nq.total_quantity_unit if nq else None,
        price_per_unit=(actual_price) / nq.total_quantity if (actual_price and nq and nq.total_quantity > 0) else None,
        raw_variant=variant_label,
        quantity_confidence=nq.confidence if nq else None,
    )


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
            log.warning(
                "Blinkit: Playwright fetch returned None for pvid=%s — "
                "returning error (not out_of_stock) to avoid false unavailable signal",
                product_id,
            )
            return ProductResult(status="error")

        snippets = result.get("response", {}).get("snippets", [])
        parsed = _parse_snippets(snippets, product_id)
        log.info(
            "Blinkit[%s] @ (%.4f,%.4f): status=%s name=%r price=%s",
            product_id, lat or 0.0, lng or 0.0, parsed.status, parsed.name, parsed.price,
        )
        return parsed

    async def product_at_location(
        self, product_id: str, lat: float, lng: float
    ) -> ProductResult:
        store = await self.resolve_store(lat, lng, product_id=product_id)
        return await self.product_at_store(product_id, store.store_id, lat=lat, lng=lng)
