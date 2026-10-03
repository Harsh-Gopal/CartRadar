import abc
import logging
from typing import Optional, Literal
from pydantic import BaseModel
import httpx
import asyncio

log = logging.getLogger("cartradar.geocoder")

class AddressResult(BaseModel):
    formatted_address: str
    short_address: str
    confidence: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    provider: str
    pincode: str | None = None

class GeocodingProvider(abc.ABC):
    @abc.abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> Optional[AddressResult]:
        pass

class NominatimProvider(GeocodingProvider):
    def __init__(self, fallback_provider: Optional[GeocodingProvider] = None):
        self.fallback = fallback_provider
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "CartRadar/1.0 (https://github.com/harshgopal/cart-radar)",
                "Accept-Language": "en-US,en;q=0.5"
            },
            timeout=10.0
        )

    async def _fetch_overpass_nearby(self, lat: float, lng: float) -> Optional[str]:
        """Fetch nearby landmarks/shops as a fallback for dark stores with no street address."""
        query = f"""
        [out:json];
        (
          node["shop"](around:250, {lat}, {lng});
          node["tourism"="hotel"](around:250, {lat}, {lng});
        );
        out 2;
        """
        try:
            resp = await self.client.get(
                "https://overpass-api.de/api/interpreter",
                params={"data": query},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for el in data.get("elements", []):
                    name = el.get("tags", {}).get("name")
                    if name:
                        return name
        except Exception as e:
            log.warning(f"Overpass fetch failed: {e}")
        return None

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[AddressResult]:
        try:
            resp = await self.client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json", "zoom": 18}
            )
            
            if resp.status_code != 200:
                log.error(f"Nominatim returned {resp.status_code}")
                if self.fallback:
                    return await self.fallback.reverse_geocode(lat, lng)
                return None
                
            data = resp.json()
            if "error" in data:
                log.warning(f"Nominatim error: {data['error']}")
                if self.fallback:
                    return await self.fallback.reverse_geocode(lat, lng)
                return None
                
            address = data.get("address", {})
            display_name = data.get("display_name", "")
            
            # Extract components
            road = address.get("road") or address.get("pedestrian") or address.get("path")
            suburb = address.get("suburb") or address.get("neighbourhood") or address.get("residential")
            city = address.get("city") or address.get("town") or address.get("village") or address.get("county")
            state = address.get("state")
            postcode = address.get("postcode")
            
            confidence = "UNKNOWN"
            short_addr_parts = []
            formatted_parts = []
            
            # Determine confidence and build addresses
            if road and suburb and city:
                confidence = "HIGH"
                short_addr_parts = [road, suburb]
                formatted_parts = [road, suburb, city, state, postcode]
            elif suburb and city:
                confidence = "MEDIUM"
                
                # Dark stores often lack road info, let's try to find a nearby landmark
                landmark = await self._fetch_overpass_nearby(lat, lng)
                if landmark:
                    short_addr_parts = [f"Near {landmark}", suburb]
                    formatted_parts = [f"Near {landmark}", suburb, city, state, postcode]
                else:
                    short_addr_parts = [suburb, city]
                    formatted_parts = [suburb, city, state, postcode]
            elif city:
                confidence = "LOW"
                short_addr_parts = [city, state]
                formatted_parts = [city, state, postcode]
            else:
                confidence = "LOW"
                short_addr_parts = [display_name.split(",")[0] if display_name else "Unknown location"]
                formatted_parts = [display_name]
                
            formatted = ", ".join([p for p in formatted_parts if p])
            short = ", ".join([p for p in short_addr_parts if p])
            
            # Fallback if parsing failed completely
            if not formatted:
                formatted = display_name
                short = display_name.split(",")[0] if display_name else "Unknown location"
                
            return AddressResult(
                formatted_address=formatted,
                short_address=short,
                confidence=confidence,
                provider="nominatim",
                pincode=postcode if postcode and len(str(postcode).strip()) == 6 and str(postcode).strip().isdigit() else None
            )
            
        except Exception as e:
            log.error(f"Reverse geocode failed: {e}")
            if self.fallback:
                return await self.fallback.reverse_geocode(lat, lng)
            return None

    async def close(self):
        await self.client.aclose()

import re
from .platforms.base import StoreResolution
# We can't import StoreCache directly due to circular dependencies, so we type hint it as Any or just duck-type it.

class StoreAddressResolver:
    """Service to resolve and cache store addresses and pincodes."""
    
    def __init__(self, geocoder: GeocodingProvider):
        self.geocoder = geocoder
        self.pincode_regex = re.compile(r'\b(\d{6})\b')
        
    def _extract_pincode(self, text: str | None) -> str | None:
        if not text:
            return None
        match = self.pincode_regex.search(text)
        return match.group(1) if match else None

    async def resolve(self, res: StoreResolution, lat: float, lng: float, cache) -> None:
        """
        Populate res.pincode and res.city based on priority:
        1. Provider-native pincode
        2. Structured address extraction
        3. Reverse geocoder fallback
        4. Regex extraction fallback
        """
        # If it's a synthetic or virtual store, don't assign physical address metadata
        if res.store_id and (res.store_id.startswith("synthetic_") or res.store_id.startswith("fm_store_")):
            return

        # Priority 1: Provider-native pincode is already on res if the provider set it
        if res.pincode and self._extract_pincode(res.pincode):
            res.pincode = self._extract_pincode(res.pincode)
            # We already have a valid pincode, but we might still need the city
            # If city is missing, we might still want to reverse geocode, but let's check cache first
        
        # Check if we already have it in cache
        cached_addr = cache.get_address(lat, lng)
        if cached_addr:
            if not res.city:
                res.city = cached_addr.formatted_address
            if not res.pincode and cached_addr.pincode:
                res.pincode = cached_addr.pincode
                
        # Priority 2: Extract from existing city/address if provider set it
        if not res.pincode and res.city:
            res.pincode = self._extract_pincode(res.city)
            
        # Priority 3: Reverse geocoding as fallback
        if not res.city or not res.pincode:
            # We need to hit Nominatim
            addr = await self.geocoder.reverse_geocode(lat, lng)
            if addr:
                if not res.city:
                    res.city = addr.formatted_address
                if not res.pincode and addr.pincode:
                    res.pincode = addr.pincode
                # Priority 4: Regex extraction from formatted address ONLY as a final fallback
                if not res.pincode:
                    res.pincode = self._extract_pincode(addr.formatted_address)
                    
                cache.save_address(lat, lng, addr)
