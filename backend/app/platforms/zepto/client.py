"""Zepto platform client using Playwright.

All Zepto-specific knowledge lives here: hosts, headers, cookies, parsing.
"""

import asyncio
import json
import logging
from urllib.parse import quote, unquote
from playwright.async_api import async_playwright

import httpx

from ..base import PlatformClient, PlatformError, ProductResult, StoreResolution
from ...normalization import parse_quantity

log = logging.getLogger("zepto")

WEB_BASE = "https://www.zeptonow.com"
BFF_BASE = "https://bff-gateway.zepto.com"
CDN_BASE = "https://cdn.zeptonow.com/production"
SAMPLE_STORE_ID = "0059ff6a-7eb0-477a-a7f5-69256f2c444b"


class ZeptoError(PlatformError):
    pass

class ZeptoWafBlockedError(ZeptoError):
    pass

class ZeptoNetworkError(ZeptoError):
    pass


def _parse_product_detail(data: dict, requested_pvid: str) -> ProductResult:
    if (data.get("fallbackType") or "NONE") != "NONE":
        return ProductResult(status="not_carried", name=(data.get("product") or {}).get("name"))
    product = data.get("product") or {}
    store_products = product.get("storeProducts") or []
    if not store_products:
        return ProductResult(status="not_carried", name=product.get("name"))
        
    # Find the specific variant requested — Zepto returns ALL variants for a product family,
    # so we must select the one matching the pvid from the user's URL.
    target_sp = None
    for sp in store_products:
        variant = sp.get("productVariant") or {}
        if variant.get("id") == requested_pvid:
            target_sp = sp
            break
            
    # Fallback: if the specific pvid isn't found (e.g. not_carried at this store),
    # use first entry only to extract metadata — mark as not_carried.
    not_found_in_store = target_sp is None
    if not_found_in_store:
        target_sp = store_products[0]
        
    sp = target_sp
    variant = sp.get("productVariant") or {}
    images = variant.get("images") or product.get("images") or []
    image_url = f"{CDN_BASE}/{images[0]['path']}" if images else None
    
    # Priority: discountedSellingPrice > sellingPrice > superSaverSellingPrice
    # Zepto stores prices in paise (1/100 of a rupee)
    price_paise = sp.get("discountedSellingPrice") or sp.get("sellingPrice") or sp.get("superSaverSellingPrice")
    mrp_paise = sp.get("mrp") or variant.get("mrp")
    price = price_paise / 100 if price_paise else None
    mrp = mrp_paise / 100 if mrp_paise else None
    
    # Determine in-stock status — if the pvid wasn't found in this store's storeProducts,
    # the product is not_carried regardless of the first entry's outOfStock flag.
    if not_found_in_store:
        status = "not_carried"
    elif sp.get("outOfStock"):
        status = "out_of_stock"
    else:
        status = "in_stock"
    
    # Variant label normalization (like all other platforms)
    # Zepto provides the variant size in productVariant.name (e.g. "750 ml", "2 L x 6")
    variant_label = variant.get("name") or variant.get("displayName") or ""
    nq = parse_quantity(variant_label) if variant_label else None
    
    return ProductResult(
        status=status,
        name=product.get("name"),
        brand=product.get("brand"),
        image_url=image_url,
        price=price,
        mrp=mrp,
        available_quantity=sp.get("availableQuantity"),
        pack_count=nq.pack_count if nq else None,
        quantity_per_pack=nq.quantity_per_pack if nq else None,
        quantity_unit=nq.quantity_unit if nq else None,
        total_quantity=nq.total_quantity if nq else None,
        total_quantity_unit=nq.total_quantity_unit if nq else None,
        price_per_unit=(price / nq.total_quantity) if (price and nq and nq.total_quantity and nq.total_quantity > 0) else None,
        raw_variant=variant_label or None,
        quantity_confidence=nq.confidence if nq else None,
    )


class ZeptoClient(PlatformClient):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def platform_name(self) -> str:
        return "zepto"

    @property
    def display_name(self) -> str:
        return "Zepto"

    @property
    def supports_sweep(self) -> bool:
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        raise NotImplementedError("Zepto now uses fetch_availability_playwright directly.")

    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        raise NotImplementedError("Zepto now uses fetch_availability_playwright directly.")

class ZeptoPlaywrightSession:
    """Manages a single Playwright browser context for Zepto sweeps to avoid WAF blocks."""
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._p = None
        self._http_client = None
        self._waf_cookies = {}

    async def __aenter__(self):
        self._p = await async_playwright().start()
        self.browser = await self._p.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        self.page = await self.context.new_page()
        # Initial WAF clearance
        log.info("Solving initial Zepto WAF...")
        await self.page.goto(f"{WEB_BASE}/", wait_until="networkidle", timeout=30000)
        await self.page.wait_for_timeout(2000)
        
        # Extract WAF cookies for fast HTTP sweep
        cookies = await self.context.cookies()
        self._waf_cookies = {
            c["name"]: c["value"] for c in cookies 
            if c["name"] not in ["serviceability", "storeId", "user_position", "selectedAddress", "addressId"]
        }
        
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()
        if self._p:
            await self._p.stop()

    async def probe_location(self, lat: float, lng: float) -> dict:
        """Sequential fast-sweep probe for a location using DOM load."""
        # Clear location-specific cookies to avoid cross-probe contamination,
        # but KEEP WAF/Datadome cookies.
        cookies = await self.context.cookies()
        keep_cookies = [c for c in cookies if c["name"] not in ["serviceability", "storeId", "user_position", "selectedAddress", "addressId"]]
        await self.context.clear_cookies()
        if keep_cookies:
            await self.context.add_cookies(keep_cookies)
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        await self.context.add_cookies([{
            "name": "user_position",
            "value": position,
            "domain": ".zepto.com",
            "path": "/"
        }, {
            "name": "user_position",
            "value": position,
            "domain": ".zeptonow.com",
            "path": "/"
        }])

        try:
            await self.page.goto(f"{WEB_BASE}/", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(0.5) # Allow server set-cookie to register
            
            cookies = await self.context.cookies()
            serviceability_cookie = next((c for c in cookies if c["name"] == "serviceability"), None)
            
            if not serviceability_cookie:
                raise ZeptoWafBlockedError("Zepto did not set a serviceability cookie.")
                
            data = json.loads(unquote(serviceability_cookie["value"]))
            primary = data.get("primaryStore") or {}
            secondary = data.get("secondaryStore") or {}
            info = data.get("storeDetailedInfo") or {}
            
            if not (primary.get("serviceable") and primary.get("storeId")):
                return {"serviceable": False}
                
            all_stores = []
            stores_data = data.get("storesData", {})
            if stores_data:
                for s_id, s_info in stores_data.items():
                    if s_info.get("serviceable"):
                        all_stores.append(s_id)
            else:
                all_stores.append(primary["storeId"])
                if secondary.get("serviceable") and secondary.get("storeId"):
                    all_stores.append(secondary["storeId"])
                    
            return {
                "serviceable": True,
                "store_id": primary["storeId"],
                "store_name": info.get("name"),
                "city": info.get("city"),
                "eta_minutes": primary.get("etaInMinutes"),
                "all_store_ids": list(set(all_stores))
            }
        except Exception as e:
            if "TimeoutError" in str(type(e)) or "Target closed" in str(e):
                raise ZeptoWafBlockedError("Playwright timed out or blocked by WAF during probe") from e
            raise ZeptoError(f"Probe failed: {e}") from e

    async def fast_sweep(self, lat: float, lng: float) -> dict:
        """Rapid HTTP HEAD request using extracted WAF cookies to discover nearby stores."""
        if not self._waf_cookies:
            raise ZeptoError("WAF cookies not initialized.")
            
        position = quote(json.dumps({"latitude": lat, "longitude": lng}, separators=(",", ":")), safe="")
        
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10.0,
                headers={
                    "Accept": "text/html",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                }
            ) as client:
                client.cookies.update(self._waf_cookies)
                client.cookies.set("user_position", position, domain=".zeptonow.com", path="/")
                client.cookies.set("user_position", position, domain=".zepto.com", path="/")
                
                resp = await client.request("HEAD", f"{WEB_BASE}/")
                
            if resp.status_code != 200:
                raise ZeptoWafBlockedError(f"HTTP fast_sweep blocked: {resp.status_code}")
                
            serviceability_cookie = resp.cookies.get("serviceability")
            if not serviceability_cookie:
                raise ZeptoError("No serviceability cookie in HTTP fast_sweep response.")
                
            data = json.loads(unquote(serviceability_cookie))
            primary = data.get("primaryStore") or {}
            secondary = data.get("secondaryStore") or {}
            info = data.get("storeDetailedInfo") or {}
            
            if not (primary.get("serviceable") and primary.get("storeId")):
                return {"serviceable": False}
                
            all_stores = []
            stores_data = data.get("storesData", {})
            if stores_data:
                for s_id, s_info in stores_data.items():
                    if s_info.get("serviceable"):
                        all_stores.append(s_id)
            else:
                all_stores.append(primary["storeId"])
                if secondary.get("serviceable") and secondary.get("storeId"):
                    all_stores.append(secondary["storeId"])
                    
            return {
                "serviceable": True,
                "store_id": primary["storeId"],
                "store_name": info.get("name"),
                "city": info.get("city"),
                "eta_minutes": primary.get("etaInMinutes"),
                "all_store_ids": list(set(all_stores))
            }
        except httpx.RequestError as e:
            raise ZeptoNetworkError(f"HTTP fast_sweep request failed: {e}") from e

    async def check_product(self, store_id: str, pvid: str) -> ProductResult:
        """Fetch product availability using the verified WAF context."""
        api_resp = await self.context.request.get(
            f"{BFF_BASE}/product-assortment-service/api/v2/product-detail?storeId={store_id}&productVariantId={pvid}",
            headers={
                "platform": "WEB",
                "tenant": "ZEPTO",
                "app_version": "16.2.11",
                "storeId": store_id
            },
            timeout=10000
        )
        
        if api_resp.status == 404:
            return ProductResult(status="not_carried")
        elif api_resp.status != 200:
            text = await api_resp.text()
            raise ZeptoNetworkError(f"Product API failed: HTTP {api_resp.status} - {text}")
        
        product_data = await api_resp.json()
        return _parse_product_detail(product_data, pvid)


class ZeptoClient(PlatformClient):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def platform_name(self) -> str:
        return "zepto"

    @property
    def display_name(self) -> str:
        return "Zepto"

    @property
    def supports_sweep(self) -> bool:
        # Sweeps are handled explicitly in Zepto's search orchestrator
        return True

    @property
    def supports_geocoding(self) -> bool:
        return False

    async def aclose(self) -> None:
        pass

    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        raise NotImplementedError("Zepto now uses ZeptoPlaywrightSession directly.")

    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        raise NotImplementedError("Zepto now uses ZeptoPlaywrightSession directly.")

    async def fetch_availability_playwright(self, lat: float, lng: float, pvid: str) -> dict:
        """Legacy helper for single-location metadata fetches (e.g. resolve_link)."""
        async with ZeptoPlaywrightSession() as session:
            try:
                res = await session.probe_location(lat, lng)
                if not res.get("serviceable") or not res.get("store_id"):
                    return {
                        "serviceable": False,
                        "store_id": None,
                        "product": None,
                        "error_reason": None
                    }
                
                product_result = await session.check_product(res.get("store_id"), pvid)
                
                # Zepto API strips product metadata (name, image) if not carried at the requested store.
                # If name is None, try known major dark stores just to extract the global product metadata.
                if not product_result.name:
                    fallback_stores = [
                        "7e5a1821-59ed-4d8a-8431-a3705afb22d2", # BLR: HSR Layout
                        "0c865653-8eac-4a33-900c-d2ed7f3c0477", # DEL: Mayur Vihar
                        "3422fce9-9587-44a5-8cff-8ee60c65617d", # DEL: Noida Sector 46
                        "809ea1fc-cf81-4257-b2b5-7d53a911cae0", # CHD: Chandigarh (Sector 38)
                        "b8aed0f4-59e0-4387-825d-406800150b71"  # DEL: Shahdara
                    ]
                    for fs_id in fallback_stores:
                        if fs_id == res.get("store_id"):
                            continue
                        try:
                            fallback_res = await session.check_product(fs_id, pvid)
                            if fallback_res.name:
                                # Steal the metadata, keep the original availability/price status
                                product_result.name = fallback_res.name
                                product_result.brand = fallback_res.brand
                                product_result.image_url = fallback_res.image_url
                                break
                        except Exception as e:
                            log.warning(f"Zepto metadata fallback failed for store {fs_id}: {e}")

                return {
                    "serviceable": True,
                    "store_id": res.get("store_id"),
                    "product": product_result,
                    "error_reason": None
                }
            except ZeptoWafBlockedError as e:
                return {
                    "serviceable": False,
                    "store_id": None,
                    "product": None,
                    "error_reason": "ACCESS_BLOCKED_OR_CHALLENGED"
                }

    async def resolve_share_link(self, url: str) -> str | None:
        return None
