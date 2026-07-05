import { useState, useEffect } from "react";

const cache = new Map<string, string>();
const pending = new Map<string, Promise<string>>();
let lastRequestTime = 0;

async function fetchPincode(lat: number, lng: number): Promise<string> {
  const key = `${lat.toFixed(4)},${lng.toFixed(4)}`;
  
  if (cache.has(key)) return cache.get(key)!;
  if (pending.has(key)) return pending.get(key)!;

  const promise = (async () => {
    const now = Date.now();
    const wait = Math.max(0, 1200 - (now - lastRequestTime));
    lastRequestTime = now + wait;
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));

    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`, {
        headers: { "User-Agent": "CartRadarApp/1.0" }
      });
      const data = await res.json();
      const postcode = data?.address?.postcode || "";
      if (postcode) {
        cache.set(key, postcode);
        return postcode;
      }
    } catch (e) {
      // ignore
    }
    return "";
  })();

  pending.set(key, promise);
  const result = await promise;
  pending.delete(key);
  return result;
}

export function usePincode(lat: number, lng: number, defaultCity?: string | null) {
  const [pincode, setPincode] = useState<string | null>(() => {
    return defaultCity?.match(/\b\d{6}\b/)?.[0] || null;
  });

  useEffect(() => {
    if (pincode) return; // Already have a pincode from city string
    let active = true;
    fetchPincode(lat, lng).then((code) => {
      if (active && code) setPincode(code);
    });
    return () => { active = false; };
  }, [lat, lng, pincode]);

  return pincode;
}
