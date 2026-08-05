<div align="center">

# 🎯 Cart Radar

**Real-time grocery stock checker across Indian quick-commerce platforms**

[![GitHub](https://img.shields.io/badge/GitHub-Harsh--Gopal-181717?logo=github)](https://github.com/Harsh-Gopal)
[![Repo](https://img.shields.io/badge/Repo-CartRadar-blue?logo=github)](https://github.com/Harsh-Gopal/CartRadar)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)

*Built and maintained by [@Harsh-Gopal](https://github.com/Harsh-Gopal)*

</div>

---

## ✨ What is Cart Radar?

Cart Radar is a web app that lets you paste any product link from a supported Indian grocery delivery platform and instantly see **which stores near you** have it in stock — including stores that aren't your default delivery zone.

Instead of just checking your nearest store, Cart Radar performs a **hex-grid sweep** of the surrounding area, probing multiple delivery zones to find every store that has the product.

---

## 🛒 Supported Platforms

| Platform | Stock Check | Area Sweep | Notes |
|---|---|---|---|
| **Zepto** | ✅ | ✅ | Hex-grid sweep across 5–30 km |
| **Swiggy Instamart** | ✅ | ✅ | Multi-zone sweep |
| **BigBasket** | ✅ | ✅ | Cookie-based location spoofing |
| **Blinkit** | ✅ | ✅ | Playwright-based |
| **BB Now** | ✅ | ❌ | Express delivery only |
| **Tata Neu** | 🚧 | 🚧 | Planned |
| **Amazon Fresh** | 🚧 | 🚧 | Planned |
| **Flipkart Minutes** | 🚧 | 🚧 | Planned |

---

## 🚀 Getting Started

> 📖 **Full step-by-step guide (all OS, troubleshooting):** [`docs/RUNNING.md`](docs/RUNNING.md)

### Prerequisites

| Tool | Install |
|---|---|
| **git** | Pre-installed on most systems |
| **uv** | `brew install uv` / [astral.sh/uv](https://astral.sh/uv) |
| **Node.js 20+ & pnpm** | `brew install node pnpm` / [pnpm.io](https://pnpm.io) |

You don't need to install Python — `uv` handles that.

### Clone

```bash
git clone https://github.com/Harsh-Gopal/CartRadar.git
cd CartRadar/cart-radar
```

### Start everything (one command)

```bash
./dev.sh
```

This starts the **FastAPI backend** (port 8000) and the **Vite dev frontend** (port 5173) together. Press Ctrl+C to stop both.

Open **[http://localhost:5173](http://localhost:5173)** when ready.

<details>
<summary>Manual start (Windows or two separate terminals)</summary>

**Backend:**
```bash
cd backend
uv sync
DEV_MODE=true ENABLED_PLATFORMS=zepto,swiggy,bigbasket,blinkit,bbnow uv run uvicorn app.main:app --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
pnpm install
pnpm dev
```
</details>

---

## 📱 How to Use

1. **Set your location** — Type an area name, locality, or pincode in the location search box. Use the GPS button to auto-detect your current location.

2. **Paste a product link** — Copy any product URL from Zepto, Swiggy, BigBasket, Blinkit, or BB Now and paste it in the product link box. The app auto-detects the platform.

3. **Set search radius** — Adjust the radius slider (5 km to 30 km) based on how far you're willing to look.

4. **Check availability** — Click "Check Availability". Results stream in real-time showing which stores have the product and at what price.

5. **View on map** — Switch to Map view to see all store pins with availability colour-coded (green = in stock, orange = out of stock).

---

## 🏗️ Architecture

```
cart-radar/
├── backend/
│   └── app/
│       ├── main.py           # FastAPI entry point, routing, auth
│       ├── search.py         # SSE orchestration, hex-grid sweep
│       ├── store_cache.py    # SQLite cache for discovered stores
│       ├── grid.py           # Haversine distance + hex-grid generator
│       ├── links.py          # URL/product-ID parser (all platforms)
│       ├── ratelimit.py      # Token bucket rate limiter
│       ├── config.py         # Environment-based configuration
│       └── platforms/
│           ├── base.py       # PlatformClient ABC
│           ├── zepto.py      # Zepto client
│           ├── swiggy.py     # Swiggy Instamart client
│           ├── bigbasket.py  # BigBasket client
│           ├── blinkit.py    # Blinkit (Playwright) client
│           └── bbnow.py      # BB Now client
└── frontend/
    └── src/
        ├── App.tsx           # Main application component
        ├── hooks/
        │   └── use-search.ts # SSE event stream hook
        ├── components/       # UI components
        └── lib/
            └── api.ts        # Backend API client
```

### Key Design Decisions

- **SSE Streaming** — Results stream in real-time via Server-Sent Events. Users see stores appear one by one as the sweep progresses, instead of waiting for all results.
- **Hex-Grid Sweep** — Store discovery uses a hexagonally-packed grid to minimize gaps and overlap while covering a circular area efficiently.
- **SQLite Store Cache** — Discovered stores and probed coordinates are cached locally (90-day TTL) to speed up repeat searches.
- **Unified Platform Interface** — All platforms implement the same `PlatformClient` ABC (`resolve_store` + `product_at_store`), making it trivial to add new platforms.
- **Token Bucket Rate Limiting** — Per-IP rate limits with daily caps prevent abuse without requiring authentication.

---

## ⚙️ Configuration

Set these environment variables to configure the backend:

| Variable | Default | Description |
|---|---|---|
| `DEV_MODE` | `false` | Disables auth token requirement |
| `APP_TOKEN` | — | Required auth token (when `DEV_MODE=false`) |
| `MAX_RADIUS_KM` | `50.0` | Maximum search radius |
| `SWEEP_SPACING_KM` | `2.0` | Spacing between hex-grid probe points |
| `MAX_CONCURRENT` | `5` | Max concurrent platform requests |
| `RATE_LIMIT_RPM` | `10` | Max requests per minute per IP |
| `RATE_LIMIT_DAILY` | `200` | Max requests per day per IP |
| `ENABLED_PLATFORMS` | all | Comma-separated list of enabled platforms |
| `DB_PATH` | `stores.sqlite3` | Path to the SQLite store cache |

---

## 🔒 Security

- **No credentials stored** — The app never stores passwords or API keys.
- **HMAC token auth** — Optional auth token uses `hmac.compare_digest` (timing-safe).
- **Input validation** — All API inputs validated via Pydantic models.
- **Rate limiting** — Token bucket per IP + daily caps prevent abuse.
- **XSS safe** — All geocode queries are URL-encoded before passing to Nominatim. All user input is treated as plain text, never rendered as HTML.

---

## 🐛 Known Issues & Roadmap

See [`docs/BUGS.md`](docs/BUGS.md) for the full bug tracker and [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) for the comprehensive audit report.

### Critical (Fixed ✅)
- **Geocode 500 error** — `httpx` import was missing in `main.py`, causing HTTP 500 on all Nominatim geocoding fallback paths. Fixed.
- **Zepto WAF bypass** — Zepto blocks automated requests (HTTP 202). Fallback to `SAMPLE_STORE_ID` for product preview. Store sweep still works.

### Planned Improvements
- [ ] Code-split JS bundle (currently 580KB — Leaflet is the main contributor)
- [ ] CORS origins via environment variable (currently hardcoded to localhost)
- [ ] Blinkit native API (replace Playwright for better sweep performance)
- [ ] Tata Neu / Flipkart Minutes / Amazon Fresh integration
- [ ] Automated test suite (pytest for backend, Vitest for frontend)
- [ ] Open Graph / SEO meta tags

---

## 🔮 Future Development

Cart Radar is under active development. Here's what's planned next — contributions welcome!

### Platform Expansion
- **Tata Neu Grocery / BB Now sweep** — Scaffolding in place; needs anti-bot bypass for full geographic sweep
- **Amazon Fresh** — Pincode-based availability check (API reverse-engineering in progress)
- **Flipkart Minutes** — Early-stage research; aggressive WAF

### Performance
- **Code-split JS bundle** — Leaflet and the map panel are lazy-loaded to cut initial load from ~580KB → ~200KB
- **Blinkit native API** — Replace Playwright-based scraping with a native HTTP client for 10× faster sweeps
- **Parallel platform sweep** — Run all platforms simultaneously for a single product link

### Features
- **Price history** — Track price changes over time using the existing SQLite store cache
- **Shareable search links** — Deep-link to a pre-filled search with product + location encoded in the URL
- **Restock alerts** — Push notifications (via Web Push API) when an out-of-stock item becomes available
- **PWA / installable** — Add manifest and service worker for offline support and home-screen install

### Infrastructure
- **CORS via environment variable** — Remove hardcoded localhost origin so any deployment domain works
- **Persistent rate limits** — Move from in-memory to SQLite-backed limits to survive server restarts
- **Docker Compose** — Single `docker compose up` for full-stack local development

### Developer Experience
- **Automated test suite** — pytest for backend platform clients + Vitest for frontend components
- **CI/CD pipeline** — GitHub Actions for lint + test on every PR

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run the build: `cd frontend && npm run build`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ by [@Harsh-Gopal](https://github.com/Harsh-Gopal) | [GitHub](https://github.com/Harsh-Gopal/CartRadar)

</div>
