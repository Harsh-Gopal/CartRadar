"""Abstract base for all platform clients.

Every instant-delivery platform (Zepto, Swiggy Instamart, BigBasket, Blinkit)
implements this interface so the search orchestrator can treat them uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoreResolution:
    """Result of asking 'which store/warehouse serves this location?'"""
    serviceable: bool
    store_id: str | None = None
    store_name: str | None = None
    city: str | None = None
    eta_minutes: int | None = None
    # Some platforms fulfil from a secondary warehouse too
    secondary_store_id: str | None = None
    secondary_eta_minutes: int | None = None


@dataclass
class ProductResult:
    """Product availability at a specific store or location."""
    status: str  # in_stock | out_of_stock | not_carried | error
    name: str | None = None
    brand: str | None = None
    image_url: str | None = None
    price: float | None = None
    mrp: float | None = None
    available_quantity: int | None = None


class PlatformError(Exception):
    """Base error for all platform-specific failures."""
    pass


class PlatformClient(ABC):
    """Every platform implements this interface.

    The search orchestrator calls these methods without caring which
    platform is being checked. Platform-specific details (hosts, headers,
    cookies, parsing) are encapsulated in each concrete subclass.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Short lowercase identifier: 'zepto', 'swiggy', 'bigbasket', 'blinkit'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name: 'Zepto', 'Swiggy Instamart', 'BigBasket', 'Blinkit'."""
        ...

    @abstractmethod
    async def aclose(self) -> None:
        """Clean up HTTP clients and other resources."""
        ...

    # -- link resolution -------------------------------------------------------

    @abstractmethod
    async def resolve_share_link(self, url: str) -> str | None:
        """Extract a product ID from a share link/pasted text.

        Returns the platform-specific product identifier (e.g. a UUID for
        Zepto, an alphanumeric ID for Swiggy) or None if unrecognised.
        """
        ...

    # -- geocoding (platform-specific) -----------------------------------------

    async def geocode(self, query: str) -> dict | None:
        """Pincode or free-text → {lat, lng, label}.

        Default: not implemented. Platforms that expose their own geocoder
        (like Zepto) override this; others rely on the unified geocoder.
        """
        return None

    async def autocomplete(self, query: str) -> list[dict]:
        """Free-text place/pincode → ranked place suggestions.

        Default: empty. Platforms with their own autocomplete override this.
        """
        return []

    # -- store resolution (the sweep primitive) --------------------------------

    @abstractmethod
    async def resolve_store(self, lat: float, lng: float, product_id: str | None = None) -> StoreResolution:
        """Which store/warehouse serves this coordinate?

        This is the core primitive for the hex-grid sweep. A HEAD or lightweight
        request that reveals the serving store without fetching product data.
        """
        ...

    # -- product availability --------------------------------------------------

    @abstractmethod
    async def product_at_store(self, product_id: str, store_id: str, lat: float | None = None, lng: float | None = None) -> ProductResult:
        """Check stock of a specific product at a specific store."""
        ...

    async def product_at_location(self, product_id: str, lat: float, lng: float) -> ProductResult:
        """Check stock at a location (resolves store first, then checks product).

        Default implementation: resolve_store → product_at_store.
        Platforms that can check availability directly by location should override.
        """
        res = await self.resolve_store(lat, lng, product_id=product_id)
        if not res.serviceable or not res.store_id:
            return ProductResult(status="not_carried")
        return await self.product_at_store(product_id, res.store_id, lat=lat, lng=lng)

    # -- capabilities ----------------------------------------------------------

    @property
    def supports_sweep(self) -> bool:
        """Whether this platform supports the hex-grid store discovery sweep.

        True means resolve_store() works well for arbitrary coordinates and
        can be called many times to map dark stores. False means only
        product_at_location() is reliable (the simpler per-pincode check).
        """
        return False

    @property
    def supports_geocoding(self) -> bool:
        """Whether this platform has its own geocoding API."""
        return False
