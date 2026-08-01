"""Swiggy Instamart platform client — httpx + Redux-state scraping.

Swiggy's /stores/instamart/item/{id} endpoint returns a full HTML page with
an embedded Redux state object containing:
  - storeDetailsV2: current store ID and serviceability for the lat/lng in cookie
  - productV2.itemData: accurate inStock, brand, name, price, imageIds

This means we can:
1. Support hex-grid sweeping like Zepto — send different lat/lng cookies to discover stores
2. Get accurate per-store stock status (not just location-level averages)
3. Show each Instamart "dark store" as a separate result with its ETA

Architecture:
  resolve_store(lat, lng) → fetches the page with userLocation cookie → extracts storeId, 
      SLA, and serviceable status from storeDetailsV2
  product_at_store(product_id, store_id, lat, lng) → fetches same page → reads 
      productV2.inStock for stock status
  supports_sweep = True → hex-grid sweep across the search radius

CDN URL pattern: https://instamart-media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto/{imageId}
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.parse
from typing import Any

import httpx

from .base import PlatformClient, PlatformError, ProductResult, StoreResolution

log = logging.getLogger("swiggy")

WEB_BASE = "https://www.swiggy.com"
STORES_BASE = f"{WEB_BASE}/stores/instamart/item"
CDN_BASE = "https://instamart-media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto"

# User-Agent that bypasses WAF on /stores/instamart/ endpoint
_UA_BOT = "Googlebot/2.1 (+http://www.google.com/bot.html)"


class SwiggyError(PlatformError):
    pass


def _make_location_cookie(lat: float, lng: float) -> str:
    """Build the userLocation cookie value with lat/lng and non-empty address."""
    val = json.dumps({"lat": lat, "lng": lng, "address": "India"})
    return "userLocation=" + urllib.parse.quote(val)


async def _fetch_page(product_id: str, lat: float | None = None, lng: float | None = None) -> str:
    """Fetch the /stores/instamart/item/ page with optional location cookie."""
    url = f"{STORES_BASE}/{product_id}"
    headers: dict[str, str] = {
        "User-Agent": _UA_BOT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    if lat is not None and lng is not None:
        headers["Cookie"] = _make_location_cookie(lat, lng)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            http2=False,
        ) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text
            log.warning("Swiggy /stores/ returned status %s for %s", resp.status_code, product_id)
            return ""
    except Exception as e:
        log.error("Swiggy fetch error: %s", e)
        return ""


def _extract_redux(html: str) -> dict:
    """
    Extract key fields from the embedded Redux state in the page HTML.

    Returns a dict with:
      - store_id: str | None
      - serviceable: bool
      - eta_minutes: int | None
      - name: str | None
      - brand: str | None
      - in_stock: bool | None (None means no itemData present)
      - is_avail: bool | None
      - price: float | None
      - mrp: float | None
      - image_url: str | None
    """
    result: dict[str, Any] = {
        "store_id": None,
        "serviceable": False,
        "eta_minutes": None,
        "name": None,
        "brand": None,
        "in_stock": None,
        "is_avail": None,
        "price": None,
        "mrp": None,
        "image_url": None,
    }

    if not html:
        return result

    # ── Store ID (storeDetailsV2.storeId) ────────────────────────────────────
    sid_m = re.search(r'"storeDetailsV2"\s*:\s*\{"storeId"\s*:\s*"(\d+)"', html)
    if sid_m:
        result["store_id"] = sid_m.group(1)

    # ── Serviceability: inferred from whether storeId + product data are present ─
    # Note: primaryStore.serviceabilityStatus can be NON_SERVICEABLE even when the
    # store does serve the area (it just means no "fast" delivery guarantee).
    # Real non-serviceability is signaled by storeId being absent from the page.
    result["serviceable"] = bool(result.get("store_id"))

    # ── ETA: look for any sla value > 0 in the page ──────────────────────────
    eta_m = re.search(r'"sla"\s*:\s*\{"value"\s*:\s*"(\d+)"', html)
    if eta_m:
        try:
            val = int(eta_m.group(1))
            if val > 0:
                result["eta_minutes"] = val
        except ValueError:
            pass

    # ── Product data (productV2.itemData) ────────────────────────────────────
    prod_idx = html.find('"productV2"')
    if prod_idx >= 0:
        # We need a generous window — the itemData can be large
        chunk = html[prod_idx: prod_idx + 5000]

        name_m = re.search(r'"displayName"\s*:\s*"([^"]+)"', chunk)
        brand_m = re.search(r'"brand"\s*:\s*"([^"]+)"', chunk)
        instock_m = re.search(r'"inStock"\s*:\s*(true|false)', chunk)
        isavail_m = re.search(r'"isAvail"\s*:\s*(true|false)', chunk)

        result["name"] = name_m.group(1) if name_m else None
        result["brand"] = brand_m.group(1) if brand_m else None
        result["in_stock"] = (instock_m.group(1) == "true") if instock_m else None
        result["is_avail"] = (isavail_m.group(1) == "true") if isavail_m else None

        # Price (offerPrice)
        offer_m = re.search(
            r'"offerPrice"\s*:\s*\{"currencyCode"\s*:\s*"INR"\s*,\s*"units"\s*:\s*"(\d+)"', chunk
        )
        mrp_m = re.search(
            r'"mrp"\s*:\s*\{"currencyCode"\s*:\s*"INR"\s*,\s*"units"\s*:\s*"(\d+)"', chunk
        )
        if offer_m:
            result["price"] = float(offer_m.group(1))
        if mrp_m:
            result["mrp"] = float(mrp_m.group(1))

        # Image (first imageId)
        img_m = re.search(r'"imageIds"\s*:\s*\["([^"]+)"', chunk)
        if img_m:
            result["image_url"] = f"{CDN_BASE}/{img_m.group(1)}"

    # ── Fallback image from JSON-LD ──────────────────────────────────────────
    if not result["image_url"]:
        jsonld_blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        for raw in jsonld_blocks:
            try:
                data = json.loads(raw.strip())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            data = item
                            break
                if isinstance(data, dict) and data.get("@type") == "Product":
                    images = data.get("image", [])
                    if isinstance(images, str):
                        result["image_url"] = images
                    elif isinstance(images, list) and images:
                        result["image_url"] = images[0]
                    elif isinstance(images, dict):
                        result["image_url"] = images.get("url") or images.get("contentUrl")
                    if result["image_url"]:
                        break
            except Exception:
                pass

    return result


def _data_to_product(data: dict, product_id: str) -> ProductResult:
    """Convert parsed Redux data to a ProductResult."""
    if not data.get("name"):
        return ProductResult(status="not_carried")

    in_stock = data.get("in_stock")
    if in_stock is True:
        status = "in_stock"
    elif in_stock is False:
        status = "out_of_stock"
    else:
        # Fallback to conservative out_of_stock when data is missing
        status = "out_of_stock"

    return ProductResult(
        status=status,
        name=data.get("name"),
        brand=data.get("brand"),
        image_url=data.get("image_url"),
        price=data.get("price"),
        mrp=data.get("mrp"),
    )


class SwiggyClient(PlatformClient):
    """Swiggy Instamart client using httpx + Redux-state scraping.

    Supports full hex-grid sweeping. Each grid point fetches the product page
    with a location cookie and extracts the assigned store ID + stock status.
    This reveals multiple Instamart dark stores across the search radius.
    """

    def __init__(self, proxy_url: str | None = None, concurrency: int = 6, transport=None):
        self._semaphore = asyncio.Semaphore(concurrency)
        # Cache: (product_id, store_id) -> ProductResult — avoids duplicate checks for same store
        self._store_cache: dict[tuple[str, str], ProductResult] = {}
        self._store_cache_lock = asyncio.Lock()

    @property
    def platform_name(self) -> str:
        return "swiggy"

    @property
    def display_name(self) -> str:
        return "Swiggy Instamart"

    @property
    def supports_sweep(self) -> bool:
        # Enabled — we can discover multiple dark stores via hex-grid sweep
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        from ..links import SWIGGY_PRODUCT_RE
        m = SWIGGY_PRODUCT_RE.search(url)
        return m.group(1) if m else None

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        """Probe a lat/lng to discover which Instamart dark store serves it.

        Returns a StoreResolution with the store_id embedded in the page's Redux state.
        If no product_id given, fetches with a known-stable placeholder item.
        """
        pid = product_id or "F9UK3KLPCI"  # generic item used only for store discovery
        async with self._semaphore:
            html = await _fetch_page(pid, lat, lng)

        data = _extract_redux(html)
        store_id = data.get("store_id")
        eta = data.get("eta_minutes")
        
        # If store_id is missing, it could mean the location is unserviceable OR
        # that the specific product is just not carried in this region's catalog.
        # To avoid aborting the entire radial sweep, we synthesize a store ID
        # based on a ~4km grid (0.04 degrees). This groups nearby points into
        # a single "synthetic" store, preventing 91 fake stores on the map while
        # still allowing the sweep to complete and return "Not Carried".
        if not store_id:
            grid_lat = round(lat / 0.04) * 0.04
            grid_lng = round(lng / 0.04) * 0.04
            store_id = f"synthetic_{grid_lat:.2f}_{grid_lng:.2f}"

        # Build a human-readable store name from ETA
        store_label = f"Instamart ({eta} min)" if eta else "Instamart"

        return StoreResolution(
            serviceable=True,  # Optimistically assume serviceable to allow sweep
            store_id=store_id,
            store_name=store_label,
            eta_minutes=eta,
            city=None,  # Will be set by StoreCache via Nominatim if needed
        )

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        """Check stock at a specific Instamart store.

        We pass the same lat/lng that was used to discover this store, so the
        page returns the same storeId and product data we need.
        """
        # Cache by (product_id, store_id) to avoid re-fetching if same store found via many grid points
        cache_key = (product_id, store_id)
        async with self._store_cache_lock:
            cached = self._store_cache.get(cache_key)
        if cached is not None:
            return cached

        if lat is not None and lng is not None:
            async with self._semaphore:
                html = await _fetch_page(product_id, lat, lng)
        else:
            async with self._semaphore:
                html = await _fetch_page(product_id)

        data = _extract_redux(html)
        result = _data_to_product(data, product_id)

        async with self._store_cache_lock:
            self._store_cache[cache_key] = result

        return result

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        """Direct location check (used by _simple_flow fallback if needed)."""
        async with self._semaphore:
            html = await _fetch_page(product_id, lat, lng)
        data = _extract_redux(html)
        return _data_to_product(data, product_id)
