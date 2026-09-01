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
                provider="nominatim"
            )
            
        except Exception as e:
            log.error(f"Reverse geocode failed: {e}")
            if self.fallback:
                return await self.fallback.reverse_geocode(lat, lng)
            return None

    async def close(self):
        await self.client.aclose()
