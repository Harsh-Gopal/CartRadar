import { useState, useEffect } from "react";

const addressCache = new Map<string, any>();

export function useAddressDetails(lat: number | undefined, lng: number | undefined) {
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lat === undefined || lng === undefined) return;
    
    const key = `${lat.toFixed(4)},${lng.toFixed(4)}`;
    
    // Check memory cache
    if (addressCache.has(key)) {
      setDetails(addressCache.get(key));
      return;
    }
    
    // Check localStorage cache
    try {
      const cached = localStorage.getItem(`addr_${key}`);
      if (cached) {
        const parsed = JSON.parse(cached);
        addressCache.set(key, parsed);
        setDetails(parsed);
        return;
      }
    } catch (e) {
      // ignore
    }

    let active = true;
    setLoading(true);

    async function fetchAddress() {
      try {
        // 1. Fetch exact address from Nominatim
        const nomRes = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=18`, {
          headers: { "User-Agent": "CartRadarApp/1.0" }
        });
        const nomData = await nomRes.json();
        
        // 2. Fetch 2 nearby shops/hotels from Overpass
        const query = `
          [out:json];
          (
            node["shop"](around:250, ${lat}, ${lng});
            node["tourism"="hotel"](around:250, ${lat}, ${lng});
          );
          out 2;
        `;
        const overpassRes = await fetch(`https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`);
        const overpassData = await overpassRes.json();
        
        const suggestions = (overpassData.elements || [])
          .map((e: any) => e.tags?.name)
          .filter(Boolean);

        const result = {
          address: nomData.display_name || "Unknown Address",
          pincode: nomData.address?.postcode || "",
          suggestions: suggestions.slice(0, 2)
        };
        
        addressCache.set(key, result);
        try {
          localStorage.setItem(`addr_${key}`, JSON.stringify(result));
        } catch (e) {}
        
        if (active) {
          setDetails(result);
          setLoading(false);
        }
      } catch (e) {
        if (active) setLoading(false);
      }
    }
    fetchAddress();

    return () => { active = false; };
  }, [lat, lng]);

  return { details, loading };
}
