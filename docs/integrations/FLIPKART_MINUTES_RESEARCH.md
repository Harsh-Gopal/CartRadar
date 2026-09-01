# Flipkart Minutes Research & Implementation

## Status: ✅ IMPLEMENTED AND VERIFIED (2026-09-01)

Flipkart Minutes (quick commerce, 10-minute delivery from dark stores) is now fully
integrated and verified to return live availability and pricing.

---

## 1. Architecture Overview

Flipkart Minutes is a hyperlocal quick commerce layer within Flipkart, identified by
the `marketplace=HYPERLOCAL` URL parameter. It is separate from standard Flipkart
(`marketplace=FLIPKART`) and requires strict geolocation for availability checks.

---

## 2. URL Types

| Type | Example | Detected As |
|---|---|---|
| Standard Flipkart | `...marketplace=FLIPKART` | `flipkart` |
| Flipkart Minutes | `...marketplace=HYPERLOCAL` | `flipkart_minutes` |
| No marketplace param | `flipkart.com/.../p/itm...` | `flipkart` |
| Short links (`dl.flipkart.com`) | Auto-resolved | Correct platform |

---

## 3. Anti-Bot Protections (Direct HTTP)

Direct `httpx`/`curl` requests hit a reCAPTCHA Enterprise wall immediately:

```html
<title>Flipkart reCAPTCHA</title>
<h1 class=header>Are you a human?</h1>
```

**Resolution:** Use Playwright (headless Chromium) with a real browser UA. The product
URL `/product/p/itme?pid=...` format avoids the CAPTCHA that `/p/itm` triggers.

---

## 4. Availability Detection Flow (Empirically Verified)

```
1. Open browser with geolocation set to user's lat/lng
2. Navigate to: https://www.flipkart.com/product/p/itme?pid={PID}&marketplace=HYPERLOCAL
3. Wait 4000ms (React renders "Use my current location" button asynchronously)
4. Click "Use my current location"
5. wait_for_url() — wait for URL to change away from hyperlocal-preview-page
   → URL CHANGED to product page = SERVICEABLE (in_stock/out_of_stock)
   → URL DID NOT CHANGE (timeout 12s) = UNSERVICEABLE (not_carried)
6. If serviceable: wait 5000ms for product content to render, then extract price
```

**Key insight:** `wait_for_url()` is ESSENTIAL. A fixed sleep is insufficient and
causes false negatives (returning `not_carried` even when serviceable).

---

## 5. Price Extraction

Flipkart Minutes product pages contain **NO `application/ld+json`** (unlike standard
Flipkart). Price is in the React DOM using obfuscated CSS class names.

**Empirically discovered class names (verified 2026-09-01):**

| Class | Content |
|---|---|
| `div.v1zwn22` | Selling/discounted price (e.g., ₹252) |
| `div.v1zwn20` | Original MRP (e.g., ₹260) |

Both classes contain multiple child elements; price must be extracted by walking text
nodes and finding the first `^₹\d` pattern within an ancestor matching the class.

---

## 6. Test Results (2026-09-01)

**Product:** Colgate Visible White Purple Toothpaste (`TPSH3PYAHTQEGTGF`)

| Location | Coords | Result |
|---|---|---|
| Bangalore city centre | 12.9716, 77.5946 | `not_carried` (unserviceable) |
| Patna Dhanaut / Hari Om Arcade | 25.6012719, 85.0697805 | ✅ `in_stock` — ₹252 / MRP ₹260 |

Patna location confirmed serviceable by user's Google Maps screenshot showing
"Delivery in 6 minutes" for the same product at that address.

---

## 7. Memory / Performance Warning

Running Playwright for Flipkart Minutes is memory-intensive:
- ~250MB per Chromium instance
- 15-25 seconds per availability check (4s render + 12s location + 5s content)
- Render free tier (512MB RAM) can OOM if multiple searches run concurrently

**Mitigation:** Playwright browser is shared (lazy singleton via `_get_browser()`),
not spawned per-request. `PLAYWRIGHT_ENABLED=false` disables Blinkit AND Flipkart
scraping entirely.

---

## 8. Fallback Strategy

If GPS geolocation fails (Flipkart doesn't accept the coordinates), the client falls
back to:
1. Reverse-geocode `lat/lng` → postcode via Nominatim (no API key, same as BigBasket)
2. Type the postcode into the "Search by area, street name, pin code" input on the
   `hyperlocal-preview-page`
3. Wait for address suggestion, click first result
4. If URL changes to product page → in_stock; otherwise → not_carried
