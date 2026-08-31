# CartRadar Bug Tracker

This document tracks known bugs, their root causes, and resolutions.

## [FIXED] Infinite Loading Screen on Search

- **Severity:** Critical
- **Affected:** All users searching for any product.
- **Root Cause:** In `App.tsx`, when a search completed (yielding a `done` event) but zero stores were found, `sortedResults.length` evaluated to `0`. The ternary operator for the status text fallback then mistakenly evaluated to `statusText`. Because `searching` was false and `totalStores` was 0, `statusText` defaulted to `"Checking on <Platform>..."`. This trapped the UI in a perpetual pseudo-loading visual state, even though the backend search had completed successfully.
- **Fix:** Updated the rendering logic in `App.tsx` so that if `state.phase === "done"` and `sortedResults.length === 0`, it displays "No stores found" and renders a "No nearby stores carry this product" message instead of indefinitely showing `statusText`.
- **Verification:** Ran local searches for URLs that return zero results due to anti-bot mechanisms or actual unavailability. The UI correctly transitions to a "No stores found" state instead of hanging.

## [FIXED] Render OOM (Memory Limit Exceeded)

- **Severity:** Critical
- **Affected:** Backend deployments on Render free tier (512 MB limit).
- **Root Cause:** The backend previously implemented a `prewarm_browser()` hook in the FastAPI `lifespan` which launched a headless Chromium instance (Playwright) during server startup. Chromium requires ~250MB+ RAM. Combined with Uvicorn and Python, this instantly exceeded the 512 MB memory limit, causing Render to forcefully restart the service in an infinite loop.
- **Fix:** Removed the `lifespan` prewarm logic. Added a `PLAYWRIGHT_ENABLED` environment variable in `config.py`. Blinkit is now entirely isolated and gated behind this flag. On low-memory deployments, you must set `PLAYWRIGHT_ENABLED=false` to avoid launching Chromium. Blinkit will be skipped gracefully.
- **Verification:** Verified that Playwright doesn't launch automatically. Render logs should confirm no OOM restarts.

## [FIXED] Search Hangs when Platform API Times Out (WAF Block)

- **Severity:** High
- **Affected:** Search functionality on platforms that block the backend IP (e.g., Zepto WAF or BigBasket Cloudflare).
- **Root Cause:** If a platform's API blocked the request or hung indefinitely, the backend SSE (`/api/search`) would remain open forever. The frontend `useSearch` hook relies on receiving a `{"type": "done"}` event to clear the loading state. 
- **Fix:** Bounded the `_sweep_flow` in `search.py` with `asyncio.wait_for(..., timeout=90.0)`. Critically, upon a `TimeoutError`, the backend catches the exception and explicitly emits a `{"type": "done"}` event with whatever partial data it collected. This ensures the frontend gracefully exits the loading state even when platform sweeps time out.
- **Verification:** Monitored SSE streams directly. Search sweeps taking longer than 90 seconds gracefully end with a `done` event instead of an `error` or hanging forever.
