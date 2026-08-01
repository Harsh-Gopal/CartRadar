from __future__ import annotations
import logging
from .base import PlatformClient, ProductResult, StoreResolution

log = logging.getLogger("amazon")

class AmazonFreshClient(PlatformClient):
    """Amazon Fresh / Amazon Now platform client.
    
    Pending implementation: Requires reverse-engineering Amazon's
    internal API or using a headless browser to bypass anti-bot protections.
    """
    
    @property
    def platform_name(self) -> str:
        return "amazon"

    @property
    def display_name(self) -> str:
        return "Amazon Fresh"

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

    async def resolve_store(
        self, lat: float, lng: float, product_id: str | None = None
    ) -> StoreResolution:
        # Scaffolding
        return StoreResolution(serviceable=False)

    async def product_at_store(
        self,
        product_id: str,
        store_id: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ProductResult:
        return ProductResult(status="not_carried")
