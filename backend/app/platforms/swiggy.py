"""Swiggy Instamart platform client — stub for API discovery.

This module will be fleshed out once we reverse-engineer the Swiggy Instamart
web API endpoints. For now it provides the structure and known URL patterns.
"""

import asyncio
import logging
import re
import urllib.parse
import json

import httpx

from .. import config
from .base import PlatformClient, PlatformError, ProductResult, StoreResolution

log = logging.getLogger("swiggy")

WEB_BASE = "https://www.swiggy.com"
USER_AGENT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)

# Swiggy Instamart product URL: /instamart/item/{product_id}
# and canonical SEO links like /instamart/p/{slug}-{product_id}
SWIGGY_PRODUCT_RE = re.compile(r"/instamart/(?:item|p)/(?:.*-)?([A-Za-z0-9_-]+)(?:[/?#]|$)")

HANDSHAKE_MAX_AGE_S = 6 * 3600
RETRY_STATUSES = {403, 429, 500, 502, 503, 504}


class SwiggyError(PlatformError):
    pass


class SwiggyClient(PlatformClient):
    _geo_cache: dict[tuple[float, float], str] = {}
    _geo_lock = asyncio.Lock()

    def __init__(
        self,
        proxy_url: str | None = None,
        concurrency: int = 5,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        kwargs = dict(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"},
        )
        if transport is not None:
            kwargs["transport"] = transport
        else:
            kwargs["proxy"] = proxy_url
        self._client = httpx.AsyncClient(**kwargs)
        self._sem = asyncio.Semaphore(concurrency)
        self._session_cookies: dict[str, str] = {}
        self._recent_checks: dict[str, ProductResult] = {}

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
        return False  # Will use Zepto's geocoder or a unified one

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- session ---------------------------------------------------------

    async def _ensure_session(self) -> None:
        """Establish a session with swiggy.com to get cookies."""
        if self._session_cookies:
            return
        pass

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        await self._ensure_session()
        last: httpx.Response | None = None
        for attempt in range(3):
            async with self._sem:
                try:
                    resp = await self._client.request(method, url, **kwargs)
                except httpx.HTTPError as e:
                    if attempt == 2:
                        raise SwiggyError(f"request failed: {e}") from e
                    await asyncio.sleep(1.5 * 2**attempt)
                    continue
            if resp.status_code not in RETRY_STATUSES:
                return resp
            last = resp
            await asyncio.sleep(1.5 * 2**attempt)
        return last  # type: ignore[return-value]

    # -- link resolution -------------------------------------------------

    async def resolve_share_link(self, url: str) -> str | None:
        m = SWIGGY_PRODUCT_RE.search(url)
        if m:
            return m.group(1)
        try:
            resp = await self._request("HEAD", url, headers={"Accept": "text/html"})
            m = SWIGGY_PRODUCT_RE.search(str(resp.url))
            if m:
                return m.group(1)
        except SwiggyError:
            pass
        return None

    # -- product fetching helper ------------------------------------------

    async def _fetch_product_page(self, product_id: str, lat: float, lng: float) -> httpx.Response:
        """Fetch the product page with location set in cookies."""
        url = f"{WEB_BASE}/instamart/item/{product_id}"
        loc = urllib.parse.quote(f'{{"lat":{lat},"lng":{lng},"address":""}}')
        headers = {"Accept": "text/html", "Cookie": f"userLocation={loc}"}
        return await self._request("GET", url, headers=headers)

    def _parse_product_state(self, state: dict) -> ProductResult:
        try:
            prod_v2 = state.get("productV2", {})
            item_data = prod_v2.get("itemData")
            
            if not item_data:
                for k, v in state.items():
                    if isinstance(v, dict):
                        if "itemInfo" in v and "item" in v["itemInfo"]:
                            item_data = v["itemInfo"]["item"]
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

            if not is_in_stock:
                return ProductResult(status="out_of_stock", name=name, brand=brand, image_url=image_url, price=price, mrp=mrp)
                
            return ProductResult(
                status="in_stock",
                name=name,
                brand=brand,
                image_url=image_url,
                price=price,
                mrp=mrp,
            )
        except Exception as e:
            log.error("Swiggy JS parse error: %s", e)
            return ProductResult(status="error")

    async def _get_location_name(self, lat: float, lng: float) -> str:
        """Resolve coordinate to a suburb / pincode via Nominatim cache."""
        rlat, rlng = round(lat, 2), round(lng, 2)
        async with self.__class__._geo_lock:
            if (rlat, rlng) in self.__class__._geo_cache:
                return self.__class__._geo_cache[(rlat, rlng)]
            
            try:
                url = f"https://nominatim.openstreetmap.org/reverse?lat={rlat}&lon={rlng}&format=json"
                async with httpx.AsyncClient(timeout=5.0) as c:
                    resp = await c.get(url, headers={"User-Agent": "CartRadarApp/1.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        address = data.get("address", {})
                        suburb = address.get("suburb", "")
                        postcode = address.get("postcode", "")
                        city = address.get("city", address.get("town", ""))
                        
                        label = ", ".join(filter(bool, [suburb, city, postcode]))
                        if label:
                            self.__class__._geo_cache[(rlat, rlng)] = label
                            await asyncio.sleep(1.2) # Hard rate limit respect
                            return label
            except Exception as e:
                log.warning("Nominatim geocoding failed: %s", e)
                
            self.__class__._geo_cache[(rlat, rlng)] = "Local Area"
            return "Local Area"

    # -- store resolution ------------------------------------------------

    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        if not product_id:
            raise SwiggyError("Swiggy resolve_store requires product_id for SSR fetch")
            
        try:
            resp = await self._fetch_product_page(product_id, lat, lng)
            if resp.status_code != 200:
                return StoreResolution(serviceable=False)
        except SwiggyError as e:
            log.warning("Swiggy resolve_store fetch failed: %s", e)
            return StoreResolution(serviceable=False)
            
        m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', resp.text)
        if not m:
            return StoreResolution(serviceable=False)
            
        try:
            state = json.loads(m.group(1))
            sd = state.get("storeDetailsV2") or {}
            store_id = sd.get("storeId")
            
            if not store_id:
                return StoreResolution(serviceable=False)
                
            eta = None
            ps = sd.get("primaryStore") or {}
            od = ps.get("orderabilityDetails") or {}
            sla = od.get("sla") or {}
            if sla.get("value"):
                try: eta = int(sla.get("value"))
                except (ValueError, TypeError): pass
                
            serviceable = (od.get("serviceabilityStatus") == "SERVICEABILITY_STATUS_SERVICEABLE")
            
            prod_result = self._parse_product_state(state)
            if prod_result.status != "error":
                self._recent_checks[f"{product_id}_{store_id}"] = prod_result
                
            
            city_label = await self._get_location_name(lat, lng)
            
            return StoreResolution(
                serviceable=serviceable,
                store_id=str(store_id),
                store_name="Instamart",
                eta_minutes=eta,
                city=city_label
            )
        except Exception as e:
            log.error("Failed to parse storeDetails: %s", e)
            return StoreResolution(serviceable=False)

    # -- product availability --------------------------------------------

    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        cache_key = f"{product_id}_{store_id}"
        if cache_key in self._recent_checks:
            res = self._recent_checks[cache_key]
            # Since sweeps cache store resolution over time, we clear this cached result so future polls force a fetch
            del self._recent_checks[cache_key]
            return res
            
        if lat is None or lng is None:
            raise SwiggyError("Swiggy requires lat/lng for product_at_store")
            
        resp = await self._fetch_product_page(product_id, lat, lng)
        if resp.status_code in (404, 400):
            return ProductResult(status="not_carried")
        if resp.status_code != 200:
            raise SwiggyError(f"HTTP {resp.status_code} blocked by WAF or failure")

        m = re.search(r'window\.___INITIAL_STATE___\s*=\s*(\{.*?\});', resp.text)
        if not m:
            raise SwiggyError("Preloaded state not found in Swiggy SSR. WAF chunking or structure changed.")
            
        state = json.loads(m.group(1))
        return self._parse_product_state(state)

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        return await super().product_at_location(product_id, lat, lng)
