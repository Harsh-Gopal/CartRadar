# 🎯 Cart Radar

**Find products in stock near you — across Zepto, Swiggy Instamart, BigBasket, and Blinkit — all at once.**

Cart Radar scans multiple quick-commerce platforms simultaneously, showing you exactly which stores near you have a product in stock, at what price, and how far away they are — all on a live map.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-indigo.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-React-blue.svg)](https://www.typescriptlang.org/)

---

## ✨ Features

- 🗺️ **Live map view** — see in-stock stores plotted on an interactive map
- ⚡ **Multi-platform scan** — Zepto, Instamart, BigBasket, Blinkit in one search
- 📍 **Adjustable radius** — scan 5 km, 10 km, 20 km, or 30 km around your location
- 💰 **Price comparison** — find the cheapest store for your product
- 📋 **Address suggestions** — copy nearby landmark addresses for delivery
- 🌙 **Dark mode** — full dark/light theme support
- 🏎️ **Hex-grid sweep** — fast parallel scanning of stores using geohex coverage
- 💾 **Store caching** — discovered stores are cached locally for faster future scans

---

## 🚀 Quick Start

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) — fast Python package manager
- [Node.js 18+](https://nodejs.org/)
- [pnpm](https://pnpm.io/installation)

### Installation

```bash
git clone https://github.com/HarshGopal/CartRadar.git
cd CartRadar/cart-radar

# Install all dependencies
cd backend && uv sync
cd ../frontend && pnpm install
cd ..

# Install Playwright browsers (needed for Blinkit + Swiggy)
cd backend && uv run playwright install chromium
```

### Run in development mode

```bash
./dev.sh
```

The app will be available at **http://localhost:5173**

The backend API runs at **http://localhost:8000**

---

## 🏗️ Architecture

```
cart-radar/
├── backend/              # FastAPI Python backend
│   └── app/
│       ├── main.py       # FastAPI app, WebSocket search endpoint
│       ├── search.py     # Search orchestrator (hex-grid sweep)
│       ├── grid.py       # Hex-grid point generation
│       ├── store_cache.py # SQLite store cache
│       ├── config.py     # Environment configuration
│       └── platforms/
│           ├── base.py       # PlatformClient ABC
│           ├── zepto.py      # Zepto (HTTP API)
│           ├── swiggy.py     # Swiggy Instamart (Playwright)
│           ├── bigbasket.py  # BigBasket (SSR scraping)
│           └── blinkit.py    # Blinkit (Playwright)
└── frontend/             # React + TypeScript frontend
    └── src/
        ├── App.tsx       # Main app component
        ├── components/   # UI components (map, results, navbar)
        ├── hooks/        # useSearch WebSocket hook
        └── lib/          # API client, utilities
```

**Tech stack:** FastAPI · httpx · Playwright · SQLite · React · TypeScript · Vite · Leaflet · shadcn/ui

---

## 🛒 Supported Platforms

| Platform | Method | Status | Notes |
|----------|--------|--------|-------|
| **Zepto** | HTTP API | ✅ Full | Hex-grid sweep, fastest |
| **BigBasket** | SSR scraping | ✅ Full | Uses location cookies |
| **Blinkit** | Playwright | ✅ Working | Slower; uses headless Chrome |
| **Swiggy Instamart** | Playwright | ⚠️ Limited | AWS WAF sometimes blocks |

> **Note on Swiggy:** Swiggy uses AWS WAF that intermittently blocks automated browsers. When blocking occurs, stores are shown as "Unavailable" rather than an error. This is a known limitation.

---

## 🔧 Configuration

Create a `.env` file in the `cart-radar/` directory (optional):

```env
# Optional: restrict access with a token
APP_TOKEN=your-secret-token

# Optional: proxy URL for all platform requests
PROXY_URL=http://user:pass@proxy.example.com:8080

# Optional: set default search radius (default: 5km, max: 30km)
DEFAULT_RADIUS_KM=5
MAX_RADIUS_KM=30
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLED_PLATFORMS` | `zepto,swiggy,bigbasket,blinkit` | Comma-separated list of platforms to enable |
| `DEV_MODE` | `false` | Disables rate limits and probe budgets |
| `APP_TOKEN` | *(none)* | If set, requires this token to use the API |
| `MAX_RADIUS_KM` | `30` | Maximum search radius allowed |
| `PROXY_URL` | *(none)* | HTTP proxy for all platform requests |

---

## 📡 API Reference

### `POST /api/resolve`
Resolve a product URL to a product ID and platform.

```json
{ "url": "https://www.zepto.com/pn/coca-cola/pvid/abc..." }
```

### `WebSocket /api/search`
Stream availability results in real-time.

```json
{
  "pvid": "abc...",
  "platform": "zepto",
  "lat": 28.6139,
  "lng": 77.2090,
  "radius_km": 5
}
```

**Events emitted:**
- `discovery_start` — sweep beginning
- `home_result` — availability at your exact location
- `store_result` — per-store availability
- `done` — search complete with summary

### `GET /api/geocode?q=<query>`
Geocode a location string.

### `GET /api/suggest?q=<query>`
Get place name suggestions.

### `GET /api/config`
Get instance configuration (enabled platforms, radius limits).

---

## 🧪 Testing

```bash
cd backend

# Run all tests
uv run pytest

# Test a specific platform manually
uv run python -c "
import asyncio
from app.platforms.zepto import ZeptoClient
async def test():
    c = ZeptoClient()
    result = await c.product_at_location('pvid-here', 28.6139, 77.2090)
    print(result)
asyncio.run(test())
"
```

---

## 📝 Example Product Links

Test Cart Radar with these real product URLs:

- **Zepto:** `https://www.zepto.com/pn/as-it-is-one-whey-protein-concentrate-2kg-unflavoured/pvid/7ea5fa66-41b8-48de-99bd-dd667193ea62`
- **Zepto:** `https://www.zepto.com/pn/as-it-is-one-whey-protein-concentrate-1kg-unflavoured/pvid/e671118a-e1fa-4ce0-9cca-762cb630391c`
- **Swiggy:** `https://www.swiggy.com/stores/instamart/item/PSHOXYIK8Y`
- **Swiggy:** `https://www.swiggy.com/stores/instamart/item/F9UK3KLPCI`
- **BigBasket:** `https://www.bigbasket.com/pd/40000263/bb-popular-toorarhar-dal-2-kg-pouch/`
- **BigBasket:** `https://www.bigbasket.com/pd/40339391/boat-type-c-c600-sturdy-cable/`

---

## 🚦 Known Limitations

1. **Swiggy WAF blocking** — AWS WAF intermittently blocks headless browsers. Products show as "Unavailable" when blocked.
2. **Rate limits** — Real IP addresses may get rate-limited after many searches. Use `PROXY_URL` in production.
3. **Blinkit slow scans** — Playwright-based scans take 15-25 seconds per grid point due to page load time.
4. **BigBasket single warehouse** — BigBasket uses city-level fulfilment, not micro dark-stores like Zepto.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgements

- [OpenStreetMap / Nominatim](https://nominatim.org/) — reverse geocoding
- [Overpass API](https://overpass-api.de/) — nearby landmark lookup
- [Leaflet.js](https://leafletjs.com/) — interactive maps
- [shadcn/ui](https://ui.shadcn.com/) — UI components
