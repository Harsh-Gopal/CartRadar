# 📋 Cart Radar — Full Audit Report

> **Author:** [@Harsh-Gopal](https://github.com/Harsh-Gopal/CartRadar) | **Date:** 2026-08-03  
> **Scope:** End-to-end QA, security, performance, accessibility, architecture  
> **Auditor:** Antigravity AI (Senior QA + Architecture Reviewer)

---

## Executive Summary

Cart Radar is a well-structured, production-capable web application for checking grocery product availability across Indian quick-commerce platforms. The architecture is clean, the code quality is generally high, and the UX is polished. 

**One critical bug was found and fixed:** `httpx` was missing from `main.py` imports, causing HTTP 500 on all Nominatim geocoding fallback paths. All other issues are medium-to-low severity improvements.

**Overall rating: 7.5/10** — Good architecture, one critical fix needed (done), several medium-priority improvements recommended.

| Category | Score | Notes |
|---|---|---|
| Architecture | 8/10 | Clean separation, good interface design |
| Code Quality | 7/10 | Mostly clean; some dead imports, fragile heuristics |
| Security | 6/10 | No auth issues, but token in localStorage, no CORS config |
| Performance | 6/10 | Bundle too large, no code splitting |
| Accessibility | 7/10 | Good ARIA basics, keyboard nav works |
| API Correctness | 8/10 | Input validation solid; 1 critical 500 bug fixed |
| Test Coverage | 3/10 | No automated tests; many test files were junk scripts |

---

## Architecture Review

### Strengths
- **Clean platform abstraction:** `PlatformClient` ABC with `resolve_store → product_at_store` pattern allows easy platform addition. The interface is stable and well-documented.
- **Hex-grid sweep is clever:** The `grid.py` hex-grid with `store_cache.py` SQLite persistence avoids redundant probes and speeds up repeat searches in the same area.
- **SSE streaming:** Real-time store results via Server-Sent Events provides excellent UX — users see results as they arrive.
- **Rate limiting:** Token bucket rate limiter per-client with global daily limits is production-appropriate.
- **Config via env vars:** All tunable settings (concurrency, rate limits, radius caps) are configurable without code changes.

### Weaknesses
- **Blinkit Playwright coupling:** Using a headless browser for stock checks means `supports_sweep = True` could launch 90+ browser pages on a sweep — a resource disaster. The Playwright approach needs a dedicated page pool or the sweep support should be disabled.
- **Single-process rate limiting:** Rate limits don't survive restarts and won't work with multiple server replicas.
- **CORS hardcoded:** `allow_origins` must be an env variable for any production deployment.
- **App.tsx is 1289 lines:** The main component has too many concerns. Should be split into: `<ProductResolver>`, `<SearchController>`, `<ResultsView>`, etc.
- **No typed SSE events:** SSE events use plain `dict`, with no shared type contract between backend and frontend. A Pydantic model on the backend and a TypeScript discriminated union on the frontend would eliminate bugs.

---

## API Behavior Summary

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/config` | GET | ✅ Working | Returns auth/radius/platforms config correctly |
| `/api/platforms` | GET | ✅ Working | All 5 platforms reported correctly |
| `/api/geocode` | GET | ✅ Fixed | Was 500 due to missing `httpx` import. Now works. |
| `/api/suggest` | GET | ✅ Fixed | Was 500 due to missing `httpx` import. Now works. |
| `/api/place` | GET | ✅ Fixed | Was 500 due to missing `httpx` import. Now works. |
| `/api/resolve` | POST | ✅ Working | Swiggy, BigBasket, Blinkit, BBNow links resolve |
| `/api/search` | GET (SSE) | ✅ Working | Swiggy sweep working; returns live results |
| `/api/stats` | GET | ✅ Working | 749 stores, 3419 probes in cache |

---

## Performance Findings

### 🔴 High Impact
- **JS bundle 580KB minified / 174KB gzip** — above the 500KB Vite warning threshold. Leaflet is a major contributor (~150KB). Code-splitting the map component would save ~150KB from initial load.

### 🟡 Medium Impact  
- **Nominatim API calls have 10s timeout** but no caching. The same location query can hit Nominatim multiple times within a session (suggest + place). A short in-memory LRU cache for geocoding results would reduce latency and respect Nominatim's 1 req/sec guideline.
- **Swiggy sweep at 10km radius probes ~91 points** — all run concurrently bounded by the 5-connection semaphore. Effective time ~20-30 seconds. Acceptable but slow for a UX perspective.

### 🟢 Low Impact
- **SQLite WAL mode enabled** — good practice for concurrent reads/writes.
- **Hex-grid probe caching (90-day TTL)** — significantly reduces repeat work.
- **LFU-style store cache with rolling average position** — elegant implementation.

---

## Security Findings

### 🟠 Medium
- **APP_TOKEN in localStorage** — Susceptible to XSS token theft. For production, migrate to `httpOnly` session cookies.
- **CORS allows only localhost** — Safe for dev, but any production deploy requires env-var-configurable origins.

### 🟡 Low
- **No rate limiting on SSE endpoint** (`/api/search`) for local requests — intentional (DEV_MODE) but worth documenting clearly.
- **XSS in geocode query** — Safely handled: the API URL-encodes the query before passing to Nominatim. No script injection risk.
- **Input validation solid** — FastAPI's Query params with `min_length` and `ge`/`le` constraints correctly reject invalid inputs (tested: 1-char queries → 422, lat > 90 → 422).
- **No SQL injection risk** — All DB queries use parameterized statements.
- **`hmac.compare_digest` for token comparison** — Correctly prevents timing attacks.

---

## Accessibility Findings

- ✅ Location search has proper `aria-label`, `role="listbox"`, `role="option"`, `aria-selected`
- ✅ GPS button has `aria-label="Use my current location"`
- ✅ Keyboard navigation (Arrow/Enter/Escape) works in suggestion dropdown
- ✅ Dark/light mode toggle accessible by click
- ⚠️ **Missing `aria-live` region** for search progress — screen readers won't announce discovery progress updates
- ⚠️ **Map pins have no keyboard access** — Leaflet markers are not focusable via Tab
- ⚠️ **Focus ring not always visible** — some buttons lack visible focus indicator in light mode

---

## Code Quality Review

### Dead Code
- `looks_like_product_link` imported in `main.py` but never called — **Fixed**
- `useAddressDetails` hook in `App.tsx` → `AddressSection` component only shown in `resolved` state but not clearly documented why

### Duplication
- `from urllib.parse import quote` was duplicated inside 3 separate function bodies in `main.py` — **Fixed** (moved to top-level import)
- `BLINKIT_PRODUCT_RE` defined in both `blinkit.py` and `links.py` — minor inconsistency

### Code Smells
- `App.tsx` at 1289 lines is a God Component — split needed
- `_extract_redux` in `swiggy.py` uses 5000-char window slicing for JSON parsing — fragile if HTML structure changes
- Swiggy's synthetic store ID fallback (`synthetic_{lat:.2f}_{lng:.2f}`) leaks into the store cache database and must be filtered/excluded in stats

---

## Technical Debt

| Item | Priority | Effort |
|---|---|---|
| Code-split map/Leaflet | High | Medium |
| CORS via env var | High | Low |
| Blinkit page pool | High | Medium |
| Split App.tsx into sub-components | Medium | High |
| Add automated pytest tests | Medium | High |
| Persist rate limits to SQLite | Medium | Medium |
| Typed SSE event schemas | Medium | Medium |
| SEO meta tags | Low | Low |
| `robots.txt` + `sitemap.xml` | Low | Low |
| Nominatim geocode cache | Low | Low |
| Tata Neu / Flipkart Minutes implementation | Future | Very High |

---

## Overall Recommendations

1. **Immediately deploy the `httpx` fix** — the 500 on geocode was breaking location search for any user whose Zepto session was blocked by the WAF.
2. **Disable Blinkit sweep or add page pool** before any serious usage — the Playwright approach will crash under load.
3. **Code-split the bundle** — 580KB on mobile connections is too heavy for Indian users on lower-end devices.
4. **Add `ALLOWED_ORIGINS` env var** before deploying to a custom domain.
5. **Add automated tests** — the project has zero `pytest` coverage. At minimum, test the `links.py` parsing functions and the `grid.py` haversine/hex functions.

---

## Platform-Specific Notes

| Platform | Status | Notes |
|---|---|---|
| **Zepto** | ✅ Working (WAF-limited) | Sweep works when Zepto session is alive. Falls back to SAMPLE_STORE_ID when WAF blocks. |
| **Swiggy Instamart** | ✅ Working | Sweep working, city=null, synthetic IDs for unserviceable zones |
| **BigBasket** | ✅ Working | SSR scraping with location cookies working |
| **Blinkit** | ⚠️ Working (risky at scale) | Playwright per-probe dangerous for sweep |
| **BB Now** | ✅ Working | Simple per-location check, no sweep |
| **Tata Neu** | 🚧 Scaffold only | No API implemented |
| **Amazon Fresh** | 🚧 Scaffold only | No API implemented |
| **Flipkart Minutes** | 🚧 Scaffold only | No API implemented |

---

## Remaining Risks

1. **Platform anti-bot measures** — Zepto, BigBasket, and Blinkit can all change their WAF/anti-bot strategies at any time. The current approach of SSR scraping is inherently fragile.
2. **Playwright memory leaks** — The Blinkit Playwright browser is never explicitly limited in memory. Under sustained load, it will exhaust RAM.
3. **SQLite concurrency** — While WAL mode helps, high concurrent writes to `probed_points` from parallel sweeps may cause occasional `database is locked` errors.
4. **Nominatim rate limits** — Nominatim enforces 1 req/sec. Under parallel geocode requests from multiple users, the server may get temporarily blocked.
