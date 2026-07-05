# Mega Stock Finder

A unified, multi-platform stock availability checker that aggregates real-time product data from quick-commerce giants like Zepto, Swiggy Instamart, and BigBasket.

![Stock Finder Demo](https://via.placeholder.com/800x400.png?text=Mega+Stock+Finder)

## How it works

1. **Paste a Link**: Share a product link from Zepto, Swiggy Instamart, or BigBasket. The app automatically detects which platform the link belongs to.
2. **Resolve Location**: Use the interactive map to pin down your exact location and set a search radius.
3. **Live Checker**: The backend orchestrates live checks against the appropriate platform's stores or fulfillment centers to show you exact real-time availability and prices.

## Supported Platforms

| Platform | Capabilities | Status |
| :--- | :--- | :--- |
| **Zepto** | Hex-grid discovery, real-time store mapping, radius scanning | ✅ Fully Supported |
| **Swiggy Instamart** | Link resolution, Pincode availability | 🚧 Dev Mode (WAF blocked*) |
| **BigBasket** | Link resolution, Pincode availability | 🚧 Dev Mode (WAF blocked*) |
| **Blinkit** | Coming soon | 🗓️ Planned |

*\*Note: Swiggy and BigBasket employ strict WAFs (AWS WAF and Akamai Bot Manager respectively) that block standard scraping tooling. The architecture fully supports them, but you must configure a robust residential proxy in `PROXY_URL` for real-world usage, otherwise the frontend will run their flows using mockup data in `DEV_MODE` to demonstrate UI readiness.*

## Tech Stack

* **Backend**: FastAPI (Python 3.13), httpx (async requests), SQLite (store caching)
* **Frontend**: React, TypeScript, Tailwind CSS, Vite
* **Architecture**: Strategy pattern (`PlatformClient` abstract component), Rate Limiting, Concurrency control

## Running the App

### Requirements
* Python 3.13 and `uv`
* Node.js / `pnpm`

### Quickstart

The fastest way to get everything running is to use the `dev.sh` script, which launches both the FastAPI backend and the Vite frontend simultaneously. It also enables all platforms in development mode.

```bash
# Clone the repository and run:
./dev.sh
```
- Frontend will be available at `http://localhost:5173`
- Backend API at `http://localhost:8400`

### Architecture & Extensions

Adding a new platform is remarkably easy:
1. Create a new file in `backend/app/platforms/`
2. Extend the `PlatformClient` class (e.g. `class BlinkitClient(PlatformClient):`)
3. Implement the required `resolve_store`, `product_at_store`, and `resolve_share_link` methods.
4. Add the platform to `ENABLED_PLATFORMS` in your environment variables.
