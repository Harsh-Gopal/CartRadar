# Cart Radar: Architecture

## Core Technology Stack

### Frontend
- **Framework:** React 18 with TypeScript, bundled via Vite.
- **Styling:** Tailwind CSS integrated with Radix UI primitives (a shadcn/ui-inspired approach) for accessible, unstyled, and highly customizable components.
- **Mapping:** `react-leaflet` wrapped around Leaflet.js for interactive rendering of store availability dots and radius bounds.
- **Icons:** `lucide-react`.

### Backend
- **Framework:** FastAPI (Python 3) running on Uvicorn.
- **Streaming:** Server-Sent Events (SSE) via `StreamingResponse` to push live stock availability checks to the frontend in real-time without blocking.
- **Scraping & Automation:** 
  - `httpx` for standard API requests (Zepto, Swiggy).
  - `playwright` (async API) for bypassing anti-bot protections and executing JavaScript on Single Page Applications (Blinkit, BigBasket).

## Architectural Patterns & Solutions

### 1. Spatial Search & Hexagonal Sweeping
To search a massive geographic area (e.g., 20km radius), the backend does not rely on a simple center-point query. 
- **Algorithm:** Uses a mathematically calculated hexagonal grid (`hex_grid` in `app/grid.py`) to systematically generate probe coordinates that blanket the requested radius. 
- **Efficiency:** The grid spacing is strictly calculated using the Haversine formula (`haversine_km`) to ensure there are no gaps in delivery coverage without overlapping unnecessarily.

### 2. High-Concurrency Playwright Management
Sweeping a 20km radius requires querying 160 individual points. Booting 160 headless Chromium browsers concurrently will instantly crash the host machine.
- **Semaphore Limiting:** We architected an `asyncio.Semaphore` bottleneck (clamped to 5 concurrent tasks) in `BlinkitClient` and `BigBasketClient`.
- **Dynamic Asynchronous Polling:** Rather than using hardcoded `asyncio.sleep` timers (which caused mass timeouts during heavy load because threads were artificially paused while browsers lagged), we implemented dynamic `while` loops that poll for XHR payload interception in Playwright (`page.route`). This allowed tasks to finish instantly upon payload reception, freeing up the semaphore rapidly.

### 3. API Interception & Header Forgery
Modern quick-commerce apps like Blinkit do not always respect HTML5 Geolocation injections.
- **Solution:** Instead of standard browser manipulation, our Playwright architecture uses `page.route("**/v1/**")` interceptors to hijack outbound XHR/Fetch requests initiated by the SPA, forcibly injecting forged `lat` and `lon` HTTP headers into the request payload. This guarantees the platform backend returns stock data for the *exact* virtual store coordinate being probed.

### 4. Multi-Layered Caching Strategy
To remain free of third-party API costs and prevent IP bans, the architecture relies heavily on caching.
- **Backend Store Cache:** An in-memory data store (`StoreCache`) retains the geographic bounding box of discovered platform warehouses (probes). If a user searches 5km, and later searches 10km, the backend skips the first 5km and instantly retrieves the cached stores.
- **Frontend Address Cache:** Address reverse-geocoding (Nominatim API) and landmark discovery (Overpass API) are cached locally in the user's browser via `localStorage` (implemented in `use-address.ts`). This ensures that re-clicking on a known coordinate instantly loads the address from memory without hitting rate-limited OSM servers.

### 5. Asynchronous Event-Driven UI
Because a 30km sweep can take up to 2-3 minutes to resolve all 200+ points across Playwright instances, the frontend uses an EventSource hook (`useSearch.ts`). The UI progressively paints dots onto the Leaflet map and updates the pricing tables live as discrete JSON events are streamed down from the FastAPI server, providing instant visual feedback rather than a long loading spinner.
