from __future__ import annotations
import logging
from .base import PlatformClient, ProductResult, StoreResolution

log = logging.getLogger("flipkart")

class FlipkartClient(PlatformClient):
    """Normal Flipkart platform client."""
    
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
        # Standard Flipkart is unsupported for 10-minute location search
        return ProductResult(
            status="error",
            price=None,
            mrp=None
        )

    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        return StoreResolution(serviceable=False)

    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        return ProductResult(status="error")


class FlipkartMinutesClient(PlatformClient):
    """Flipkart Minutes platform client.
    
    Due to aggressive WAF/reCAPTCHA and lack of a public web API,
    Flipkart Minutes cannot be reliably scraped without bypassing anti-bot protections.
    """
    
    @property
    def platform_name(self) -> str:
        return "flipkart_minutes"

    @property
    def display_name(self) -> str:
        return "Flipkart Minutes"

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
        return ProductResult(status="error")

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        return StoreResolution(serviceable=False)

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        return ProductResult(status="error")
