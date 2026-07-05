"""BigBasket platform client — SSR-based availability checker.

BigBasket uses Next.js SSR. Each product page at /pd/{product_id}/ embeds
full availability + pricing data in a <script id="__NEXT_DATA__"> tag.
Location is signalled via HTTP cookies sent with the page request:

    _bb_lat_long      = base64(lat|lng)
    _bb_addressinfo   = base64(lat|lng|area_name|pincode|city|...)
    _bb_sa_ids        = service-area IDs (optional, improves accuracy)

The response contains `productDetails.children[]` — each child is a variant
(pack size). `avail_status == "001"` means in-stock at the given location.

Sweep strategy: BigBasket has a single fulfilment warehouse per city / pin-code
region, not many micro dark-stores like Zepto. We model each location as
a "virtual store" keyed by (rounded_lat, rounded_lng) so the hex-grid sweep
still works and different city pin-codes map to different stores.
"""

import asyncio
import base64
import json
import logging
import re
from datetime import datetime

import httpx

from .. import config
from .base import PlatformClient, PlatformError, ProductResult, StoreResolution
from ..grid import haversine_km

log = logging.getLogger("bigbasket")

WEB_BASE = "https://www.bigbasket.com"

# BigBasket product URL: /pd/{product_id}/{slug}/
BB_PRODUCT_RE = re.compile(r"/pd/(\d+)(?:[/?#]|$)")

RETRY_STATUSES = {403, 429, 500, 502, 503, 504}

# ── headers that mimic a real Chrome browser ──────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


class BigBasketError(PlatformError):
    pass


def _make_cookies(lat: float, lng: float, area_name: str = "", pincode: str = "", city: str = "") -> str:
    """Build the BigBasket location cookies required by the SSR renderer.
    
    Uses URL-safe base64 (no +, /, = issues in cookie values).
    """
    # _bb_lat_long: base64( lat|lng )
    lat_long_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}".encode()).decode().rstrip("=")

    # _bb_addressinfo: base64( lat|lng|area|pincode|city )
    addr_b64 = base64.urlsafe_b64encode(
        f"{lat}|{lng}|{area_name}|{pincode}|{city}".encode()
    ).decode().rstrip("=")

    return (
        f"_bb_lat_long={lat_long_b64}; "
        f"_bb_addressinfo={addr_b64}; "
        f"_bb_pin_code={pincode}; "
    )


class BigBasketClient(PlatformClient):
    """BigBasket client — SSR page scraping with location cookies."""

    # Class-level Nominatim cache (shared across instances) 
    _geo_lock: asyncio.Lock | None = None
    _geo_cache: dict[tuple[float, float], dict] = {}

    def __init__(
        self,
        proxy_url: str | None = None,
        concurrency: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        kwargs: dict = dict(
            timeout=httpx.Timeout(25.0),
            follow_redirects=True,
            headers=_HEADERS,
        )
        if transport is not None:
            kwargs["transport"] = transport
        elif proxy_url:
            kwargs["proxy"] = proxy_url

        self._client = httpx.AsyncClient(**kwargs)
        self._sem = asyncio.Semaphore(concurrency)
        self._session_initialized = False

        if self.__class__._geo_lock is None:
            self.__class__._geo_lock = asyncio.Lock()

        # Cache of recently fetched product results (keyed by "pvid_lat_lng")
        self._recent_checks: dict[str, ProductResult] = {}

    # ── identity ──────────────────────────────────────────────────────────────

    @property
    def platform_name(self) -> str:
        return "bigbasket"

    @property
    def display_name(self) -> str:
        return "BigBasket"

    @property
    def supports_sweep(self) -> bool:
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── geocoding helper ──────────────────────────────────────────────────────

    async def _reverse_geocode(self, lat: float, lng: float) -> dict:
        """Return {area, pincode, city} for the given coordinates via Nominatim."""
        async with self.__class__._geo_lock:
            # Re-use the closest cached geocode if it's within 40km (covers a whole sweep)
            # This ensures we get the EXACT pincode of the center point for the whole grid,
            # avoiding 1-sec delays per point while keeping the pincode accurate for the city.
            closest = None
            min_dist = 9999
            for (clat, clng), data in self.__class__._geo_cache.items():
                dist = haversine_km(lat, lng, clat, clng)
                if dist < min_dist:
                    min_dist = dist
                    closest = data
            
            if closest and min_dist <= 40:
                return closest

            # Not found or too far, fetch exact coordinates from Nominatim
            rlat, rlng = round(lat, 4), round(lng, 4)
            result: dict = {"area": "", "pincode": "", "city": ""}
            try:
                url = (
                    f"https://nominatim.openstreetmap.org/reverse"
                    f"?lat={rlat}&lon={rlng}&format=json&addressdetails=1"
                )
                async with httpx.AsyncClient(timeout=8.0) as c:
                    resp = await c.get(url, headers={"User-Agent": "CartRadarApp/1.0 (stock-checker)"})
                    if resp.status_code == 200:
                        data = resp.json()
                        addr = data.get("address", {})
                        result["area"] = (
                            addr.get("neighbourhood")
                            or addr.get("suburb")
                            or addr.get("quarter")
                            or addr.get("village")
                            or ""
                        )
                        result["pincode"] = addr.get("postcode", "")
                        result["city"] = (
                            addr.get("city")
                            or addr.get("town")
                            or addr.get("county")
                            or ""
                        )
                # Respect Nominatim 1 req/sec rate limit
                await asyncio.sleep(1.1)
            except Exception as e:
                log.warning("Nominatim reverse-geocode failed: %s", e)

            self.__class__._geo_cache[(rlat, rlng)] = result
            return result

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if not self._session_initialized:
            self._session_initialized = True
            try:
                await self._client.get(WEB_BASE + "/", headers={"Accept": "text/html"})
            except Exception as e:
                log.warning("BB session init failed: %s", e)
                
        last: httpx.Response | None = None
        for attempt in range(3):
            async with self._sem:
                try:
                    resp = await self._client.request(method, url, **kwargs)
                except httpx.HTTPError as e:
                    if attempt == 2:
                        raise BigBasketError(f"request failed: {e}") from e
                    await asyncio.sleep(1.5 * 2 ** attempt)
                    continue
            if resp.status_code not in RETRY_STATUSES:
                return resp
            last = resp
            await asyncio.sleep(1.5 * 2 ** attempt)
        raise BigBasketError(f"Persistent HTTP {last.status_code if last else '?'} from BigBasket")

    # ── link resolution ────────────────────────────────────────────────────────

    async def resolve_share_link(self, url: str) -> str | None:
        m = BB_PRODUCT_RE.search(url)
        if m:
            return m.group(1)
        try:
            resp = await self._request("GET", url, headers={"Accept": "text/html"})
            m = BB_PRODUCT_RE.search(str(resp.url))
            if m:
                return m.group(1)
        except BigBasketError:
            pass
        return None

    # ── SSR page fetch + parsing ───────────────────────────────────────────────

    async def _fetch_product_page(self, product_id: str, lat: float, lng: float) -> str:
        """Fetch the BigBasket product page with location cookies set."""
        
        # Reverse geocode to get the pincode, which is strictly required by BigBasket
        # for accurate local stock. We use an 11km cache grid so it only takes ~1s per sweep.
        geo = await self._reverse_geocode(lat, lng)
        area = geo.get("area", "")
        pincode = geo.get("pincode", "")
        city = geo.get("city", "")

        # Build location cookies as a dict so httpx handles them properly
        lat_long_b64 = base64.urlsafe_b64encode(f"{lat}|{lng}".encode()).decode().rstrip("=")
        addr_b64 = base64.urlsafe_b64encode(
            f"{lat}|{lng}|{area}|{pincode}|{city}".encode()
        ).decode().rstrip("=")
        
        self._client.cookies.set("_bb_lat_long", lat_long_b64, domain=".bigbasket.com")
        self._client.cookies.set("_bb_addressinfo", addr_b64, domain=".bigbasket.com")
        self._client.cookies.set("_bb_pin_code", pincode, domain=".bigbasket.com")

        url = f"{WEB_BASE}/pd/{product_id}/"
        try:
            resp = await self._request(
                "GET",
                url,
                headers={**_HEADERS, "Referer": WEB_BASE + "/"},
            )
            if resp.status_code == 200:
                return resp.text
            log.warning("BB product page returned HTTP %s for pvid=%s", resp.status_code, product_id)
            return ""
        except BigBasketError as e:
            log.warning("BB fetch failed: %s", e)
            return ""

    def _extract_next_data(self, html: str) -> dict | None:
        """Extract and parse the __NEXT_DATA__ JSON block from HTML."""
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    def _parse_product_state(self, state: dict, product_id: str) -> ProductResult:
        """Parse __NEXT_DATA__ and return availability for the given product_id."""
        try:
            page_props = state.get("props", {}).get("pageProps", {})
            product_details = page_props.get("productDetails", {})
            children: list[dict] = product_details.get("children", [])

            # Find the variant matching the requested product_id.
            # BigBasket's `id` field is the variant/SKU id; try matching by
            # numeric id or by the parent product id (which may appear on the
            # parent `product_details` node itself).
            target: dict | None = None
            for child in children:
                if (
                    str(child.get("id")) == product_id
                    or str(child.get("sku_id")) == product_id
                ):
                    target = child
                    break

            # If no exact match, just use the first (default) child.
            if not target and children:
                target = children[0]
                log.debug(
                    "BB pvid=%s not matched in children; using first child id=%s",
                    product_id,
                    target.get("id"),
                )

            if not target:
                return ProductResult(status="not_carried")

            # Availability status codes
            avail = target.get("availability", {})
            avail_status = avail.get("avail_status")  # "001" = in_stock
            status = "in_stock" if avail_status == "001" else "out_of_stock"

            # Pricing
            # Structure: pricing.discount.mrp (str) + pricing.discount.prim_price.sp (str)
            pricing = target.get("pricing", {})
            discount = pricing.get("discount", {})
            try:
                mrp_raw = discount.get("mrp", 0)
                mrp = float(mrp_raw) if mrp_raw else None
            except (TypeError, ValueError):
                mrp = None
            prim_price = discount.get("prim_price", {}) or pricing.get("prim_price", {}) or {}
            try:
                sp_raw = prim_price.get("sp", 0)
                sp = float(sp_raw) if sp_raw else None
            except (TypeError, ValueError):
                sp = None
            price = sp or mrp

            # Name / brand - both live directly on the child node
            name = (target.get("desc") or "").strip() or None
            brand_node = target.get("brand") or {}
            if isinstance(brand_node, dict):
                brand = brand_node.get("name", "")
            elif isinstance(brand_node, str):
                brand = brand_node
            else:
                brand = ""

            # Image URL
            images = target.get("images", [])
            image_url: str | None = None
            if images and isinstance(images, list):
                img = images[0]
                image_url = img.get("m") or img.get("s") or img.get("l")

            if status != "in_stock":
                return ProductResult(
                    status=status,
                    name=name or None,
                    brand=brand or None,
                    image_url=image_url,
                    price=price,
                    mrp=mrp,
                )

            return ProductResult(
                status="in_stock",
                name=name or None,
                brand=brand or None,
                image_url=image_url,
                price=price,
                mrp=mrp,
            )
        except Exception as e:
            log.error("BB parse error: %s", e, exc_info=True)
            return ProductResult(status="error")

    # ── store resolution ───────────────────────────────────────────────────────

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        """Map a lat/lng to a BigBasket 'virtual store' for the hex-grid sweep.

        BigBasket serves by pin-code area rather than many micro dark-stores.
        We create a virtual store ID from the rounded coordinates so that
        the store cache can deduplicate areas we've already mapped.
        """
        # Use cached pincode to group BigBasket virtual stores efficiently.
        # Since _reverse_geocode returns the center pincode instantly for the
        # whole sweep, this ensures we don't spam identical stock checks.
        geo = await self._reverse_geocode(lat, lng)
        pincode = geo.get("pincode", "unknown")
        store_id = f"bb_{pincode}"
        store_name = f"BigBasket Area ({pincode})"

        serviceable = True

        if product_id:
            # Opportunistically fetch the product and cache the result
            html = await self._fetch_product_page(product_id, lat, lng)
            if html:
                state = self._extract_next_data(html)
                if state:
                    result = self._parse_product_state(state, product_id)
                    if result.status != "error":
                        cache_key = f"{product_id}_{store_id}"
                        self._recent_checks[cache_key] = result

        return StoreResolution(
            serviceable=serviceable,
            store_id=store_id,
            store_name=store_name,
            eta_minutes=None,
            city=None,
        )

    # ── product availability ──────────────────────────────────────────────────

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        """Check availability of a product at a 'virtual' BB store.

        Uses a freshly-fetched SSR page (with location cookies) to get live data.
        Cache the result from resolve_store if available to save an extra request.
        """
        cache_key = f"{product_id}_{store_id}"
        if cache_key in self._recent_checks:
            result = self._recent_checks.pop(cache_key)
            return result

        if lat is None or lng is None:
            return ProductResult(status="error")

        html = await self._fetch_product_page(product_id, lat, lng)
        if not html:
            return ProductResult(status="error")

        state = self._extract_next_data(html)
        if not state:
            # Page loaded but no Next.js data — product may not exist
            if "404" in html[:2000] or "not found" in html[:2000].lower():
                return ProductResult(status="not_carried")
            return ProductResult(status="error")

        return self._parse_product_state(state, product_id)

    async def product_at_location(
        self, product_id: str, lat: float, lng: float
    ) -> ProductResult:
        """Direct location check — resolve store then check product."""
        store = await self.resolve_store(lat, lng, product_id=product_id)
        if not store.store_id or not store.serviceable:
            return ProductResult(status="not_carried")
        return await self.product_at_store(product_id, store.store_id, lat=lat, lng=lng)
