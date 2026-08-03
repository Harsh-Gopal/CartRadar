# 🐛 Cart Radar — Bug Tracker

> Maintained by: [@Harsh-Gopal](https://github.com/Harsh-Gopal/CartRadar)  
> Last audited: 2026-08-03  
> Audit scope: Full end-to-end (backend API, frontend UI, security, performance, accessibility)

---

## 🔴 Critical

### BUG-001 — `httpx` Missing Import Causes 500 on Geocode/Suggest/Place Fallback
| Field | Details |
|---|---|
| **Status** | ✅ Fixed |
| **Affected Files** | `backend/app/main.py` |
| **Root Cause** | `httpx` was used in the Nominatim fallback for `/api/geocode`, `/api/suggest`, and `/api/place` but was never imported. Any query that bypassed Zepto's geocoding raised `NameError: name 'httpx' is not defined`, resulting in HTTP 500. |
| **Reproduction** | Enter any generic text in location search. Observe HTTP 500. |
| **Expected** | 404 "Location not found" or empty suggestions |
| **Fix Applied** | Added `import httpx` and `from urllib.parse import quote` to top-level imports. |

---

## 🟠 High

### BUG-002 — Zepto WAF Block Silently Degrades Store Resolution
| Field | Details |
|---|---|
| **Status** | ⚠️ Partially Mitigated |
| **Affected Files** | `backend/app/platforms/zepto.py`, `backend/app/main.py` |
| **Root Cause** | Zepto WAF returns HTTP 202. When blocked, falls back to `SAMPLE_STORE_ID` — a placeholder that may be in a completely different city, showing wrong stock status. |
| **Recommended Fix** | Show "Preview unavailable for your area" in UI when SAMPLE_STORE_ID is used. |

### BUG-003 — Swiggy Sweep Aborted for Out-of-Catalog Products
| Field | Details |
|---|---|
| **Status** | ✅ Fixed (workaround) |
| **Affected Files** | `backend/app/platforms/swiggy.py` |
| **Root Cause** | When Swiggy returns no `storeId` (product not in local catalog), sweep aborted with `serviceable=False`. Caused 0 stores in secondary cities like Patna. |
| **Fix Applied** | Synthetic store IDs on ~4km grid allow sweep to continue. |

### BUG-004 — CORS Origins Hardcoded to localhost:5173
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `backend/app/main.py` |
| **Root Cause** | `allow_origins` is hardcoded. Production deployments on custom domains will be CORS-blocked. |
| **Recommended Fix** | Move to `ALLOWED_ORIGINS` environment variable. |

### BUG-005 — Blinkit Playwright Sweep Could Launch 91 Browser Pages Concurrently
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `backend/app/platforms/blinkit.py` |
| **Root Cause** | `supports_sweep = True` but each probe requires a Playwright browser page. 10km radius ≈ 91 points — will crash server. |
| **Recommended Fix** | Set `supports_sweep = False` until a native API is found, or add tight concurrency limits. |

---

## 🟡 Medium

### BUG-006 — JS Bundle Exceeds 500KB
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/vite.config.ts` |
| **Root Cause** | Single bundle of 580KB. Leaflet, icon sets loaded upfront. Vite build shows warning on every build. |
| **Recommended Fix** | Dynamic `import()` for Leaflet and `react-leaflet`. Code-split results map. |

### BUG-007 — `looksResolvable()` Doesn't Handle New Zepto `/pn/` URLs
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/src/App.tsx` |
| **Root Cause** | Frontend gating only checks `/pvid/`. Backend `links.py` was updated for `/pn/` format but frontend wasn't. |
| **Expected** | New Zepto `/pn/` URLs trigger auto-resolve |
| **Actual** | User must click "Check" manually |
| **Recommended Fix** | Update regex in `looksResolvable` to include `/pn/` pattern. |

### BUG-008 — `getPlatformFromId` Uses Fragile Heuristics
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/src/components/results-list.tsx` |
| **Root Cause** | Detects platform from store ID string patterns. Swiggy numeric IDs can overlap with other platforms. |
| **Recommended Fix** | Use `r.platform` field directly (it's already in the SSE payload). |

### BUG-009 — Swiggy Store `city` Always `null`
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `backend/app/platforms/swiggy.py` |
| **Root Cause** | `city=None` is always set in `StoreResolution`. No city label on Swiggy store results. |
| **Recommended Fix** | Reverse geocode via Nominatim, or parse from Swiggy HTML `storeDetailsV2.address`. |

### BUG-010 — `autoRan` Ref Never Resets on Product Change
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/src/App.tsx` |
| **Root Cause** | `autoRan.current` stays `true` after `resetToStart()`. Next product won't auto-search. |
| **Reproduction** | Search product A → click logo to reset → search product B → no auto-search fires. |
| **Recommended Fix** | Add `autoRan.current = false` in `resetToStart()`. |

### BUG-011 — Rate Limiter Resets on Server Restart
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `backend/app/ratelimit.py` |
| **Root Cause** | All limits are in-memory. Daily limits can be bypassed by restarting server. |
| **Recommended Fix** | Persist rate limits to SQLite. |

### BUG-012 — Blinkit No Page Pool (Race Condition Risk)
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `backend/app/platforms/blinkit.py` |
| **Root Cause** | Shared `_BROWSER` with no page pool. Concurrent probes create/close pages on same browser simultaneously. |
| **Recommended Fix** | `asyncio.Queue`-based page pool with max 4 pages. |

---

## 🟢 Low

### BUG-013 — Junk Test/Dev Files in `backend/` Directory
| Field | Details |
|---|---|
| **Status** | ✅ Fixed |
| **Fix Applied** | All `test_blinkit_*.py`, `*.html` snapshots, `*.png`, `*.json` state files removed. |

### BUG-014 — No SEO Meta Tags
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/index.html` |
| **Root Cause** | No `<meta name="description">`, Open Graph, or Twitter card tags. |
| **Recommended Fix** | Add standard SEO and OG meta tags. |

### BUG-015 — Token Stored in localStorage (XSS Risk)
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/src/lib/api.ts` |
| **Root Cause** | `APP_TOKEN` stored as plaintext in localStorage. XSS could exfiltrate it. |
| **Recommended Fix** | Use `httpOnly` cookies for token in production. |

### BUG-016 — Nominatim User-Agent Was Generic
| Field | Details |
|---|---|
| **Status** | ✅ Fixed |
| **Fix Applied** | Updated to `CartRadar/1.0 (github.com/Harsh-Gopal/CartRadar)` per Nominatim policy. |

### BUG-017 — Navbar "How it works" Links to GitHub Repo Root
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Recommended Fix** | Link to README.md section or dedicated docs page. |

### BUG-018 — No `robots.txt` or `sitemap.xml`
| Field | Details |
|---|---|
| **Status** | 🔵 Open |
| **Affected Files** | `frontend/public/` |
| **Recommended Fix** | Add `robots.txt` allowing all bots and a basic sitemap. |
