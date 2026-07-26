"""BB Now platform client — BigBasket's express delivery arm (Tata Neu).

BB Now (bbnow.bigbasket.com) is BigBasket's 30-minute express delivery service,
powering the grocery section inside the Tata Neu app.

Key facts:
  - Shares the same product IDs as BigBasket (/pd/{numeric_id}/)
  - Same Next.js SSR page structure with __NEXT_DATA__
  - Same location cookies as BigBasket (_bb_lat_long, _bb_addressinfo)
  - Availability field: child.availability.avail_status
      "001" = in_stock (express available)
      anything else = out_of_stock / not available for express

Coverage: Major Indian metros — Delhi, Mumbai, Bengaluru, Hyderabad, Pune, Chennai.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re

import httpx

from .base import PlatformClient, PlatformError, ProductResult, StoreResolution

log = logging.getLogger("bbnow")

WEB_BASE = "https://bbnow.bigbasket.com"

# In-stock avail_status codes for BB Now
_IN_STOCK_CODES = {"001"}

RETRY_STATUSES = {429, 500, 502, 503, 504}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

# BB Now product URL regex — same format as BigBasket
BBNOW_PRODUCT_RE = re.compile(r"/pd/(\d+)(?:[/?#]|$)")


class BBNowError(PlatformError):
    pass


def _build_location_cookies(lat: float, lng: float) -> dict[str, str]:
    """Build the location cookies BB Now/BigBasket use for availability."""
    lat_lng_b64 = base64.b64encode(f"{lat}|{lng}".encode()).decode()
    addr_b64 = base64.b64encode(
        f"{lat}|{lng}|Local Area|000000|City|State|India".encode()
    ).decode()
    return {
        "_bb_lat_long": lat_lng_b64,
        "_bb_addressinfo": addr_b64,
    }


async def _fetch_product_page(
    product_id: str,
    lat: float | None = None,
    lng: float | None = None,
) -> str:
    """Fetch the BB Now product page HTML."""
    url = f"{WEB_BASE}/pd/{product_id}/"
    cookies = _build_location_cookies(lat, lng) if lat is not None else {}

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                resp = await client.get(url, headers=_HEADERS, cookies=cookies)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in RETRY_STATUSES and attempt < 2:
                    await asyncio.sleep(1.5 ** attempt)
                    continue
                log.warning(
                    "BB Now product page returned %s for %s", resp.status_code, product_id
                )
                return ""
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1.5 ** attempt)
                continue
            log.error("BB Now fetch error for %s: %s", product_id, e)
            return ""
    return ""


def _parse_next_data(html: str) -> dict:
    """Extract __NEXT_DATA__ JSON from HTML."""
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _html_to_product(html: str, product_id: str) -> ProductResult:
    """Parse BB Now product page HTML into a ProductResult."""
    if not html:
        return ProductResult(status="not_carried")

    data = _parse_next_data(html)
    product_details = (
        data.get("props", {})
        .get("pageProps", {})
        .get("productDetails", {})
    )

    if not product_details:
        log.warning("BB Now: no productDetails in __NEXT_DATA__ for %s", product_id)
        return ProductResult(status="not_carried")

    children = product_details.get("children", [])
    if not children:
        return ProductResult(status="not_carried")

    # Use the first/primary variant
    child = children[0]

    # -- Availability --
    availability = child.get("availability", {}) or {}
    avail_status = availability.get("avail_status", "")
    is_in_stock = str(avail_status) in _IN_STOCK_CODES

    # -- Name --
    name = child.get("desc") or product_details.get("desc")
    if not name:
        return ProductResult(status="not_carried")

    # Pack description
    pack_desc = child.get("pack_desc")
    if pack_desc and pack_desc not in name:
        name = f"{name} {pack_desc}"

    # -- Brand --
    brand_raw = child.get("brand", {})
    brand: str | None = None
    if isinstance(brand_raw, dict):
        brand = brand_raw.get("name") or brand_raw.get("brand_name")
    elif isinstance(brand_raw, str) and brand_raw:
        brand = brand_raw

    # -- Image --
    image_url = None
    images = child.get("images", [])
    if images and isinstance(images, list):
        first_img = images[0]
        if isinstance(first_img, dict):
            image_url = first_img.get("s") or first_img.get("m") or first_img.get("l")
        elif isinstance(first_img, str):
            image_url = first_img
    # Fallback: construct a known bbassets CDN URL
    if not image_url:
        image_url = f"https://www.bbassets.com/media/uploads/p/m/{product_id}_1-{product_id}.jpg"

    # -- Price --
    price: float | None = None
    mrp: float | None = None
    pricing = child.get("pricing", {}) or {}
    discount = pricing.get("discount", {}) or {}
    prim_price = discount.get("prim_price", {}) or {}
    sp_val = prim_price.get("sp")
    mrp_val = discount.get("mrp")
    try:
        price = float(sp_val) if sp_val else None
    except (TypeError, ValueError):
        price = None
    try:
        mrp = float(mrp_val) if mrp_val else price
    except (TypeError, ValueError):
        mrp = price

    return ProductResult(
        status="in_stock" if is_in_stock else "out_of_stock",
        name=name.strip(),
        brand=brand,
        image_url=image_url,
        price=price,
        mrp=mrp,
    )


class BBNowClient(PlatformClient):
    """BB Now (Tata Neu express grocery) client — Next.js SSR scraping.

    BB Now is BigBasket's 30-minute express delivery service. It uses the
    same product IDs as BigBasket but checks a different availability field
    (avail_status "001" = in-stock for express delivery).

    Note: BB Now does NOT support the hex-grid sweep — it's a single-location
    check (is this product available for express delivery at my coordinates?).
    """

    def __init__(self, proxy_url: str | None = None, concurrency: int = 4, transport=None):
        self._semaphore = asyncio.Semaphore(concurrency)

    @property
    def platform_name(self) -> str:
        return "bbnow"

    @property
    def display_name(self) -> str:
        return "BB Now"

    @property
    def supports_sweep(self) -> bool:
        return False

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_share_link(self, url: str) -> str | None:
        m = BBNOW_PRODUCT_RE.search(url)
        return m.group(1) if m else None

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        """BB Now does not expose store-level APIs — returns a virtual store."""
        return StoreResolution(
            serviceable=True,
            store_id=f"bbnow_{round(lat, 3)}_{round(lng, 3)}",
            store_name="BB Now",
            eta_minutes=30,
        )

    async def product_at_location(
        self, product_id: str, lat: float, lng: float
    ) -> ProductResult:
        """Check BB Now express availability for a product at a location."""
        async with self._semaphore:
            html = await _fetch_product_page(product_id, lat, lng)
            return _html_to_product(html, product_id)

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        """Check product availability (uses lat/lng if provided)."""
        async with self._semaphore:
            html = await _fetch_product_page(product_id, lat, lng)
            return _html_to_product(html, product_id)
