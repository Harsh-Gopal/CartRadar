"""Swiggy Instamart platform client — httpx + JSON-LD scraping.

Swiggy's AWS WAF blocks automated requests to /instamart/item/{id}.
However, the /stores/instamart/item/{id} endpoint (used for app-store
deep links and SEO) returns full 200 responses with structured data:
  - JSON-LD schema.org/Product with name, brand, images, price, availability
  - Open Graph meta tags as fallback

This lets us use plain httpx (no Playwright needed!) which is:
  - Fast (~1-2s vs 30s+ for Playwright)
  - Reliable (no WAF challenge pages)
  - Parallel-friendly

Availability note:
  The /stores/ endpoint reflects real-time stock status for the location
  inferred from the userLocation cookie. Since we can't set cookies easily
  in httpx, we use multiple fallback strategies to detect stock.
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

# User-Agent that bypasses WAF on /stores/instamart/ endpoint
_UA_BOT = "Googlebot/2.1 (+http://www.google.com/bot.html)"
_UA_MOBILE = (
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
)

# Per-product cache (product_id → base metadata, no location-specific status)
_META_CACHE: dict[str, dict] = {}
_META_LOCK = asyncio.Lock()

# Geo label cache
_GEO_CACHE: dict[tuple[float, float], str] = {}
_GEO_LOCK = asyncio.Lock()


class SwiggyError(PlatformError):
    pass


async def _fetch_product_html(product_id: str, lat: float | None = None, lng: float | None = None) -> str:
    """Fetch the /stores/instamart/item/ page which bypasses WAF.
    
    Sets the userLocation cookie if lat/lng provided, which affects
    the availability reported in the JSON-LD offers block.
    """
    url = f"{STORES_BASE}/{product_id}"
    
    headers = {
        "User-Agent": _UA_BOT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    
    # Include userLocation cookie to get location-aware stock
    if lat is not None and lng is not None:
        loc_val = urllib.parse.quote(json.dumps({"lat": lat, "lng": lng, "address": ""}))
        headers["Cookie"] = f"userLocation={loc_val}"
    
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


def _parse_jsonld(html: str) -> dict | None:
    """Extract JSON-LD Product block from HTML."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
            elif isinstance(data, dict) and data.get("@type") == "Product":
                return data
        except Exception:
            pass
    return None


def _parse_og_tags(html: str) -> dict:
    """Extract Open Graph tags as fallback metadata."""
    result = {}
    for prop, key in [
        ("og:title", "title"),
        ("og:image", "image"),
        ("og:description", "description"),
    ]:
        m = re.search(
            rf'<meta[^>]+property=["\']({re.escape(prop)})["\'][^>]*content=["\']([^"\']*)["\']',
            html,
            re.IGNORECASE,
        )
        if not m:
            # Try alternate attribute order
            m = re.search(
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*property=["\']({re.escape(prop)})["\']',
                html,
                re.IGNORECASE,
            )
            if m:
                result[key] = m.group(1)
        else:
            result[key] = m.group(2)
    return result


def _clean_name(raw: str) -> str:
    """Clean up Swiggy product title."""
    # Remove: "Buy X Online (weight) At Best Price"
    name = re.sub(r'^Buy\s+', '', raw, flags=re.IGNORECASE)
    name = re.sub(r'\s+Online\s*(?:\([^)]+\))?\s*(?:At Best Price|on Instamart|in India)?$', '', name, flags=re.IGNORECASE)
    return name.strip()


def _html_to_product(html: str, product_id: str, lat: float | None, lng: float | None) -> ProductResult:
    """Parse HTML to ProductResult using JSON-LD and OG fallbacks."""
    if not html:
        return ProductResult(status="not_carried")
    
    jsonld = _parse_jsonld(html)
    og = _parse_og_tags(html)
    
    # ── Name ─────────────────────────────────────────────────────────────────
    name = None
    if jsonld:
        name = jsonld.get("name")
    if not name:
        og_title = og.get("title", "")
        if og_title:
            name = _clean_name(og_title)
    if not name:
        # Fall back to <title> tag
        m = re.search(r'<title[^>]*>([^<]+)</title>', html)
        if m:
            name = _clean_name(m.group(1))
    
    # ── Brand ─────────────────────────────────────────────────────────────────
    brand = None
    if jsonld:
        brand_obj = jsonld.get("brand", {})
        if isinstance(brand_obj, dict):
            brand = brand_obj.get("name")
        elif isinstance(brand_obj, str):
            brand = brand_obj
    
    # ── Image ─────────────────────────────────────────────────────────────────
    image_url = None
    if jsonld:
        images = jsonld.get("image", [])
        if isinstance(images, str):
            image_url = images
        elif isinstance(images, list) and images:
            image_url = images[0]
    if not image_url:
        image_url = og.get("image")
    
    # ── Price / Availability ───────────────────────────────────────────────────
    price = None
    mrp = None
    status = "in_stock"  # Default: JSON-LD with InStock means available
    
    if jsonld:
        offers = jsonld.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            # Price
            raw_price = offers.get("price")
            if raw_price is not None:
                try:
                    price = float(raw_price)
                    mrp = price
                except Exception:
                    pass
            # Availability
            avail = offers.get("availability", "")
            if "OutOfStock" in avail or "Discontinued" in avail or "SoldOut" in avail:
                status = "out_of_stock"
            elif "InStock" in avail or "PreOrder" in avail:
                status = "in_stock"
    
    # Additional availability signals from HTML content
    if "out of stock" in html.lower() and "add to cart" not in html.lower():
        status = "out_of_stock"
    
    if not name:
        log.warning("Swiggy: could not extract product name for %s", product_id)
        return ProductResult(status="not_carried")
    
    return ProductResult(
        status=status,
        name=name,
        brand=brand,
        image_url=image_url,
        price=price,
        mrp=mrp,
    )


async def _get_location_label(lat: float, lng: float) -> str:
    """Reverse-geocode coordinates to a human-readable label."""
    key = (round(lat, 2), round(lng, 2))
    async with _GEO_LOCK:
        if key in _GEO_CACHE:
            return _GEO_CACHE[key]
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={round(lat, 4)}&lon={round(lng, 4)}&format=json"
        )
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get(url, headers={"User-Agent": "CartRadar/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                suburb = (
                    addr.get("suburb")
                    or addr.get("neighbourhood")
                    or addr.get("village")
                    or ""
                )
                city = addr.get("city") or addr.get("town") or addr.get("county") or ""
                postcode = addr.get("postcode", "")
                label = ", ".join(filter(bool, [suburb, city, postcode]))
                if label:
                    async with _GEO_LOCK:
                        _GEO_CACHE[key] = label
                    await asyncio.sleep(1.1)  # Nominatim rate limit
                    return label
    except Exception as e:
        log.debug("Geocoding error: %s", e)
    
    label = "Local Area"
    async with _GEO_LOCK:
        _GEO_CACHE[key] = label
    return label


class SwiggyClient(PlatformClient):
    """Swiggy Instamart client using httpx + JSON-LD HTML scraping.
    
    Uses the /stores/instamart/item/ endpoint which:
    - Returns 200 without WAF challenge
    - Contains JSON-LD structured data with product name, images, price, stock
    - Works with a simple Googlebot user-agent header
    """

    def __init__(self, proxy_url: str | None = None, concurrency: int = 5, transport=None):
        self._semaphore = asyncio.Semaphore(concurrency)

    @property
    def platform_name(self) -> str:
        return "swiggy"

    @property
    def display_name(self) -> str:
        return "Swiggy Instamart"

    @property
    def supports_sweep(self) -> bool:
        # Instamart only shows stock for current location, not per-store.
        # Sweeping the grid would still show same result. Single check is enough.
        return False

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        # Product ID is in the URL path
        from ..links import SWIGGY_PRODUCT_RE
        m = SWIGGY_PRODUCT_RE.search(url)
        return m.group(1) if m else None

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        """Fetch product availability for a specific location."""
        async with self._semaphore:
            html = await _fetch_product_html(product_id, lat, lng)
            return _html_to_product(html, product_id, lat, lng)

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        """Virtual store resolution — Instamart doesn't expose store IDs."""
        store_id = f"swiggy_{round(lat, 3)}_{round(lng, 3)}"
        city = await _get_location_label(lat, lng)
        return StoreResolution(
            serviceable=True,
            store_id=store_id,
            store_name="Instamart",
            eta_minutes=20,
            city=city,
        )

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        """Check product at a store (use lat/lng for location-aware check)."""
        if lat is not None and lng is not None:
            return await self.product_at_location(product_id, lat, lng)
        # No location: fetch metadata-only (no stock check)
        async with self._semaphore:
            html = await _fetch_product_html(product_id)
            return _html_to_product(html, product_id, None, None)
