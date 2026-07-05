# Cart Radar: Project Context

## Project Overview
Cart Radar is a full-stack web application designed to check the real-time stock availability of specific products across major quick-commerce and e-commerce platforms in India, specifically: **Zepto, Swiggy Instamart, BigBasket, and Blinkit**.

The application allows users to paste a product link, parses the product ID, and maps out its availability within a customizable geographic radius (e.g., 5km, 10km, 20km, 30km) using a hexagonal grid sweeping algorithm. 

## Known Issues, Bugs, and Resolutions

### 1. Blinkit "Check Failed" on Large Sweeps (Resolved)
- **Issue:** Scanning a 5km radius worked perfectly, but scanning 10km (34 points) or 20km (160 points) resulted in massive "Check failed" errors for Blinkit.
- **Root Cause:** Playwright concurrency load. The `blinkit.py` scraper had a hardcoded `await asyncio.sleep(2.0)` to wait for the XHR response. Under the heavy load of a 10km+ sweep, the API naturally took 3-5 seconds to respond, causing the server to prematurely close the browser context before the data arrived.
- **Resolution:** Replaced the hardcoded sleep with a dynamic `while product_json is None` loop that polls every 0.1s and can wait up to 15 seconds if the system is under load. 

### 2. Blinkit Showing "In Stock" when "Out of Stock" (Resolved)
- **Issue:** Blinkit would falsely report a product as "In Stock" for a specific location when the real Blinkit app showed it as "Out of Stock".
- **Root Cause:** The Playwright backend wasn't correctly injecting the `lat` and `lon` headers into Blinkit's `/v1/layout/product` API requests. Without these headers, Blinkit fell back to a default location (where the product happened to be in stock).
- **Resolution:** Added a Playwright route interceptor (`page.route("**/v1/**")`) that forcibly injects the `lat` and `lon` headers into the API request, ensuring stock data strictly matches the queried coordinates. (We also specifically targeted `**/v1/**` instead of `**/*` to prevent Cloudflare from blocking the main page load).

### 3. BigBasket False Availability (Resolved)
- **Issue:** BigBasket showed products as available even when they were out of stock in real life at that pincode.
- **Resolution:** Improved BigBasket scraping logic and coordinate mapping to ensure it queries the specific local store availability rather than a generic regional catalog.

### 4. Search Radius Exceeding User Input (Resolved)
- **Issue:** A user setting the slider to 5km would see red dots (stores) showing up 10km away.
- **Root Cause:** The `search.py` cache retrieval logic was using an aggressively padded bounding box (`radius_km + GRID_SPACING_KM`). Since `GRID_SPACING_KM` was 3.0, it fetched cached stores up to 8km-10km away.
- **Resolution:** Removed the `GRID_SPACING_KM` padding from the final cache filter, forcing the map to strictly respect the user's requested `radius_km`.

### 5. Address Generation Inaccuracies & API Limits (Resolved)
- **Issue:** The app generated generic addresses, and hitting the address generation API constantly risked rate limits. 
- **Resolution:** Integrated the **Nominatim (OpenStreetMap)** API for reverse geocoding, supplemented by the **Overpass API** to fetch 2 nearby landmarks (shops/hotels) for highly accurate virtual addresses. 
- **Caching:** Implemented aggressive caching in `frontend/src/lib/use-address.ts` using `localStorage` and memory maps. Once an address is generated for a coordinate, it is saved instantly, dramatically speeding up subsequent searches and preserving API quotas.

### 6. "Search Limit Reached" Errors (Resolved)
- **Issue:** Users were prematurely hitting "Search limit reached" or HTTP 500 errors.
- **Resolution:** Addressed backend rate limiting logic and optimized concurrent requests (like the 160-point sweeps) to reduce CPU overhead and prevent the backend from bottlenecking and crashing under concurrent search pressure.

## Current State & Open Items
- **UI Aesthetics:** The UI has been heavily refined away from a "generic AI-generated" look to a premium, modern design with dark/light mode support, smooth radius sliders, and detailed bottom-sheet drawers for store information.
- **Default Radius:** The default search radius is intentionally clamped to **5km** to ensure speedy, reliable first-paints, with the user retaining the option to manually scrub up to 30km.
