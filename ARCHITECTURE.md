# Cart Radar: Architecture

## 1. System Overview

Cart Radar is a full-stack web application designed to check real-time stock availability of specific products across major Indian quick-commerce and e-commerce platforms. 

The application flow follows this sequence:
1. **User input:** User provides a product URL and geographic coordinates to the React frontend.
2. **Frontend request:** The frontend establishes a Server-Sent Events (SSE) connection to the FastAPI backend.
3. **Product resolution:** The backend identifies the platform and normalizes the product ID.
4. **Store discovery:** The backend queries its local SQLite cache for known delivery zones/warehouses in the area, and simultaneously performs a hex-grid spatial sweep to discover new stores.
5. **Live stock checks:** For every store discovered (cached or new), the backend executes a live stock check against the platform.
6. **SSE streaming:** Results (in-stock, out-of-stock, unserviceable) are progressively streamed back to the frontend.
7. **UI updates:** The frontend immediately renders discovered stores on an interactive map and list view.

## 2. Frontend Architecture

The frontend is a modern Single Page Application (SPA).

- **Core Stack:** React 18, TypeScript, bundled via Vite.
- **Styling:** Tailwind CSS integrated with accessible UI primitives (shadcn-like approach) and Lucide icons.
- **Mapping:** `react-leaflet` wrapped around Leaflet.js for interactive rendering of store locations, stock status (color-coded dots), and radius bounds.
- **State & Streaming:** Custom React hooks (`use-search.ts`) manage the `EventSource` lifecycle. The UI progressively paints results as discrete JSON events stream in from the backend, avoiding long loading spinners.
- **Address Search:** Integrated map search and reverse geocoding allow users to drop pins or search locations natively.
- **Local Caching:** User preferences (last searched location, radius, watchlist) are persisted in the browser's `localStorage`.

## 3. Backend Architecture

The backend is a high-performance Python ASGI service.

- **Core Stack:** FastAPI running on Uvicorn.
- **Event Streaming:** Uses `StreamingResponse` to push SSE events to the frontend in real-time.
- **Spatial Processing:** Haversine distance calculations and hex-grid generation (`app/grid.py`) to blanket circular search radii efficiently.
- **Concurrency & Rate Limiting:** Implements token-bucket rate limiting per IP (`app/ratelimit.py`) and strict `asyncio.Semaphore` constraints to prevent crashing the host server under heavy concurrent load.
- **HTTP Clients:** `httpx.AsyncClient` for highly concurrent, lightweight API scraping.
- **Headless Browsers:** `playwright` (async) for platforms employing aggressive anti-bot/WAF measures (e.g., Blinkit, Zepto hybrid sweep).
- **Geocoding:** Reverse geocoding endpoint (`/api/reverse_geocode`) backed by Nominatim, allowing the frontend to resolve coordinates into human-readable addresses.

## 4. Platform Client Implementations

All platform scrapers inherit from a base `PlatformClient` ABC, enforcing a standardized contract (`resolve_store` and `product_at_store`).

- **Zepto:** Uses a "Hybrid Sweep" architecture. Since Zepto employs aggressive WAF/Datadome protection, Cart Radar uses a headless Playwright Chromium context to seamlessly pass the WAF and extract session cookies. These verified cookies are then passed to a highly concurrent `httpx.AsyncClient` for extreme-speed hex-grid sweeping.
- **Swiggy Instamart:** Pure `httpx` async client. Handles multi-zone store discovery gracefully.
- **BigBasket:** Cookie-based location spoofing and HTTP scraping.
- **Blinkit:** Full Playwright-based client. Uses API interception (`page.route("**/v1/**")`) to inject forged `lat` and `lon` HTTP headers into the SPA's outbound XHR requests, bypassing HTML5 Geolocation restrictions. Inventory states (`is_sold_out`, `inventory`) are parsed directly from the matched identity snippet.
- **Flipkart & Flipkart Minutes:** Robust HTTP client utilizing specialized metadata headers and cached coordinates for rapid serviceability and stock resolution.
- **BB Now:** Pure HTTP client focused strictly on express delivery zones.

*(Note: Tata Neu and Amazon Fresh are planned integrations but not currently implemented.)*

## 5. Hex-Grid Search System

To search a massive geographic area (e.g., 20km radius), Cart Radar cannot rely on a single center-point query. Delivery platforms restrict queries to strict geofenced polygons.

1. **Grid Generation:** The backend calculates a mathematically optimal hexagonal grid (`hex_grid`) to blanket the requested radius.
2. **Spacing:** The spacing is calculated using the Haversine formula to ensure no gaps in delivery coverage without overlapping unnecessarily.
3. **Probing:** The backend iterates through these generated coordinates, querying the platform's serviceability API for each point.
4. **Deduplication:** When a store/warehouse responds, its unique ID is added to a `set()`. If multiple grid points land inside the same delivery zone, the redundant checks are skipped.
5. **Streaming:** As soon as a unique store is resolved and its stock is checked, the backend yields an SSE event to the frontend.

## 6. Cache Architecture

Cart Radar employs a heavily optimized, multi-layered caching strategy to maximize speed and minimize API abuse.

### Store Discovery Cache (SQLite)
The backend maintains a persistent SQLite database (`app/store_cache.py`).
- **What is cached:** The *existence* of a dark-store/warehouse, its physical coordinates, its platform-specific ID, and its general serviceability metadata.
- **TTL:** Serviceable stores are cached for 90 days. Unserviceable dead-zones are cached for 30 days.
- **How it works:** When a user searches a 10km radius, the backend first queries the SQLite database for all known stores within 10km. It skips probing grid points that fall near already-cached stores, massively accelerating the search.

### Stock Status (NOT Cached)
- **Live Checks:** Product stock levels, prices, and availability are **never** cached as a long-lived discovery asset. Even if a store is loaded instantly from the SQLite discovery cache, the backend still executes a fresh, live stock check against that store.

### Re-check Stock (Force Mode)
- **Behavior:** The frontend provides a "Re-check Stock" button. Clicking this passes `force=True` to the backend.
- **Cache Bypass:** When `force=True`, the backend ignores the SQLite discovery cache entirely. It forces a 100% fresh hex-grid sweep of the entire area, re-probing every coordinate and executing fresh live stock checks.

## 7. Reliability & Resilience

- **Playwright Concurrency:** Playwright instances (e.g., Blinkit) are heavily restricted by an `asyncio.Semaphore` (clamped to a small number of concurrent tasks) to prevent CPU/RAM exhaustion on the host machine.
- **Dynamic Asynchronous Polling:** Rather than using hardcoded `sleep` timers, Playwright scrapers utilize dynamic `while` loops that poll for intercepted XHR payloads (`page.route`), allowing tasks to finish instantly upon payload reception.
- **Differentiating Failures:** The system distinguishes between "out of stock" (the platform explicitly returned 0 inventory or an OOS flag) and "check failed" (the scraper timed out or the WAF blocked the request). Failed checks are reported as errors, preventing false "Out of Stock" assumptions.

## 8. Docker & Deployment Architecture

Cart Radar is containerized and distributed via pre-built images.

- **Containers:** A `backend` FastAPI container and a `frontend` Vite/Nginx container orchestrate together via Docker Compose.
- **GHCR Images:** Pre-built images are hosted on the GitHub Container Registry (`ghcr.io`).
- **Multi-Platform:** GitHub Actions build and publish native images for both `linux/amd64` (Intel/AMD) and `linux/arm64` (Apple Silicon/Raspberry Pi) architectures using QEMU cross-compilation.
- **User Workflow:** Non-technical users interact with Cart Radar using OS-specific one-click launchers (`Cart Radar.command`, `.bat`, `.sh`). These launchers automatically resolve paths, verify Docker Desktop health, pull the latest images, start the containers, and launch the browser to `http://localhost:3000`.

## 9. Development Architecture

Contributors working on the source code bypass Docker to enable hot-reloading:

- **Script:** `./dev.sh`
- **Backend:** Runs natively via `uv` on `http://localhost:8000`.
- **Frontend:** Runs natively via `pnpm` on `http://localhost:5173`.
- **Requirements:** Requires Node.js 22+ (for SQLite tooling) and Python `uv`.
