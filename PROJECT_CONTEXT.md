# Cart Radar: Project Context

## 1. Project Overview

Cart Radar is a full-stack web application that allows users to paste a grocery/quick-commerce product link and instantly see real-time availability across their entire city. 

Currently implemented and supported platforms:
- Zepto
- Swiggy Instamart
- BigBasket
- Blinkit
- Flipkart
- Flipkart Minutes
- BB Now

The application utilizes a hexagonal grid sweeping algorithm to probe geographic areas (up to a 30km radius), bypassing standard "nearest store" limitations to find exactly where a product is in stock.

## 2. Current Repository Structure

```
CartRadar/
├── ARCHITECTURE.md
├── PROJECT_CONTEXT.md
├── README.md
├── dev.sh                     # Native development start script
├── docker-compose.yml         # Production/normal user container config
├── Cart Radar.command         # macOS one-click everyday launcher
├── Cart Radar Install.command # macOS one-click install launcher
├── (Other OS launchers)
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & API routes
│   │   ├── search.py          # SSE orchestration, hex-grid sweep logic
│   │   ├── store_cache.py     # SQLite persistent store/discovery cache
│   │   ├── grid.py            # Haversine distance + hex-grid generator
│   │   ├── links.py           # Universal URL/product-ID parser
│   │   ├── ratelimit.py       # Token bucket rate limiting per IP
│   │   ├── config.py          # Environment configuration
│   │   └── platforms/         # Individual scraper/client implementations
│   └── tests/                 # Pytest suite
└── frontend/
    └── src/
        ├── App.tsx            # Main application UI component
        ├── components/        # React components (map, results list)
        ├── hooks/             # SSE event stream & geocoding hooks
        └── lib/               # Utility functions & API clients
```

## 3. Current Technology Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Leaflet (`react-leaflet`), Lucide React.
**Backend:** Python 3, FastAPI, Uvicorn, SQLite, Playwright (async), `httpx` (async).
**Infrastructure:** Docker Compose, GitHub Actions, GHCR (GitHub Container Registry).

## 4. Current Platform Support

| Platform | Product Resolution | Live Stock Check | Area Sweep | Special Implementation Notes |
|---|---|---|---|---|
| **Zepto** | ✅ | ✅ | ✅ | Playwright Hybrid Sweep (WAF bypass -> fast httpx) |
| **Swiggy Instamart** | ✅ | ✅ | ✅ | Multi-zone sweep |
| **BigBasket** | ✅ | ✅ | ✅ | Cookie-based location spoofing |
| **Blinkit** | ✅ | ✅ | ✅ | Full Playwright client; API interception (`page.route`) |
| **Flipkart Minutes** | ✅ | ✅ | ✅ | Robust metadata & cached coordinates |
| **BB Now** | ✅ | ✅ | ❌ | Express delivery only (no wide sweep) |

## 5. Search & Discovery Flow

The typical lifecycle of a user search request:

1. **Resolve:** User inputs URL -> Backend identifies platform and canonical product ID.
2. **Locate:** User sets target coordinate (lat/lon) and search radius (e.g., 10km).
3. **Cache Lookup:** Backend queries SQLite `store_cache` for all known warehouses within 10km.
4. **Grid Generation:** Backend generates a hex-grid of probe points covering the 10km radius.
5. **Sweep Execution:** Backend skips grid points near cached stores, and probes the remaining undiscovered points.
6. **Stock Check:** A live stock check is executed against every resolved store (both cached and newly discovered).
7. **Cache Update:** Newly discovered stores are deduplicated and saved to the SQLite discovery cache.
8. **SSE Stream:** As each live stock check completes, an SSE JSON event is yielded to the frontend.
9. **Render:** The frontend progressively paints the interactive Leaflet map and populates the results list.

## 6. Cache & Re-check Rules

Understanding the caching distinction is critical to the architecture:

- **Store Discovery Cache (Cached):** The *existence* of a physical delivery zone, its coordinates, and its metadata are persisted in a local SQLite database (`app/store_cache.py`). Serviceable stores live for 90 days. This prevents the backend from needlessly re-scanning known areas.
- **Stock Status (NOT Cached):** Actual product availability, inventory counts, and prices are **never** cached. Normal searches load stores from the discovery cache and *immediately* execute fresh stock checks against them.
- **Re-check Stock (Force Mode):** Clicking the "Re-check Stock" button in the UI passes `force=True` to the backend. This completely bypasses the SQLite discovery cache and forces the backend to mathematically re-probe the entire hex-grid from scratch, ensuring 100% fresh discovery.

## 7. Reliability Fixes & Historical Issues

Important resolved issues explaining why the code behaves the way it does:

- **Blinkit Stock Availability Accuracy:**
  - *Problem:* Blinkit falsely reported products as Out of Stock, or missed inventory numbers entirely.
  - *Root Cause:* The scraper attempted to read inventory from specific UI "widget" types. However, Blinkit's API sets `widget=None` for all snippets.
  - *Resolution:* Logic rewritten to locate the identity-matched snippet (`data.identity.id == product_id`) and extract `inventory`, `is_sold_out`, and `product_state` directly. Stock accuracy is now 100%.

- **Blinkit Large-Radius Failures:**
  - *Problem:* Sweeping 20km (160 points) caused massive "Check failed" errors and Playwright crashes.
  - *Root Cause:* Hardcoded `asyncio.sleep` timers were locking up the event loop under heavy concurrent browser load.
  - *Resolution:* Implemented dynamic `while` polling against intercepted `page.route` payloads, allowing tasks to finish instantly upon API response.

- **Zepto Datadome WAF Blocks:**
  - *Problem:* Zepto blocked headless HTTP scrapers instantly via Datadome.
  - *Resolution:* Implemented the "Hybrid Sweep" architecture. A single Playwright instance organically clears the WAF to extract session cookies, which are then passed to an ultra-fast async HTTP client for the actual sweeping.

- **Address Generation Limits:**
  - *Problem:* Constant reverse-geocoding hit API rate limits.
  - *Resolution:* Backend implemented a robust `/api/reverse_geocode` route using Nominatim, backed by the SQLite persistent cache.

- **Docker ARM64 Compatibility:**
  - *Problem:* Apple Silicon (M1/M2/M3) Macs threw `no matching manifest for linux/arm64/v8` when pulling GHCR images.
  - *Resolution:* Added `docker/setup-qemu-action@v3` to GitHub Actions, allowing the AMD64 GitHub runners to cross-compile and publish multi-platform `linux/amd64` and `linux/arm64` images.

## 8. Current Docker & Distribution State

- **Deployment:** Pre-built Docker images are published to the GitHub Container Registry (`ghcr.io/harsh-gopal/cartradar-frontend` and `cartradar-backend`).
- **Platform Support:** Images are compiled for both AMD64 and ARM64.
- **Normal Workflow:** Users execute OS-specific one-click scripts (`Cart Radar.command`, `.bat`, etc.) which handle Docker Compose invocation automatically, safely handling working-directory resolution regardless of where the folder was unzipped.
- **Port:** The Docker stack exposes the frontend application on `http://localhost:3000`.

## 9. Testing & Validation

- **Backend Pytest Suite:** The backend includes a dedicated test suite (`tests/`). It features 15 comprehensive unit tests (as of the latest reliability pass) validating local dev rate limits, link extraction logic (including Flipkart short URLs and minutes params), and Blinkit stock parsing logic (`in_stock`, `out_of_stock`, and `not_carried` scenarios).
- **Frontend Validation:** The Vite frontend enforces strict TypeScript compilation (`tsc -b`) before production builds. Node.js 22+ is required for the frontend build environment to support modern SQLite tooling in `pnpm 11+`.

## 10. Known Limitations

- **API Volatility:** Quick-commerce platforms frequently update their undocumented APIs or increase WAF protections, which can temporarily break platform scrapers.
- **Resource Intensive:** Playwright-backed platforms (Blinkit) consume significantly more CPU and memory than standard HTTP clients.
- **Sweep Duration:** A full 30km radius un-cached sweep requires querying hundreds of coordinates and can take over a minute to resolve completely.

## 11. Future Work

- **Tata Neu & Amazon Fresh:** Planned integrations for future geographic coverage.
- **Price History:** Utilizing the existing SQLite database to track historical price changes over time.
- **Restock Alerts:** Push notifications via the Web Push API when an out-of-stock item returns to inventory.
- **Shareable Searches:** Deep-linking support to encode product URLs and coordinates directly into the frontend URL state.
- **PWA Support:** Service worker implementation for offline support and mobile home-screen installation.
