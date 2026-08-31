# System Robustness Audit

This document outlines the architectural safety and robustness guarantees implemented to ensure CartRadar operates reliably under constraints (specifically memory limits on Render) and external platform unreliability.

## 1. Playwright Memory Safety (OOM Prevention)

CartRadar integrates Playwright (Chromium) specifically to scrape Blinkit due to their aggressive obfuscation. Headless Chromium consumes substantial memory (~250-300MB). 
- **Problem:** Deploying on Render's free tier (512MB RAM) caused Out Of Memory (OOM) crashes because Chromium was pre-warmed on server startup.
- **Robustness Measure:** 
  1. Playwright initialization is strictly lazy; it only launches upon the first request to Blinkit.
  2. The `PLAYWRIGHT_ENABLED` flag (configured in `config.py` and via environment variables) acts as a hard gate. If set to `false`, the `BlinkitClient` is completely skipped.
  3. This ensures low-memory environments never crash due to headless browser allocation. You must configure `PLAYWRIGHT_ENABLED=false` on Render free tier.

## 2. Real-Time Serviceability vs. Static Guesses

- **Problem:** Previously, the platform determined "Delivery Hours" using static tables of operating hours (e.g., assuming Zepto is 24x7 in metros and closes at 11 PM elsewhere). This is brittle and inaccurate during adverse weather, store outages, or dynamic demand surges.
- **Robustness Measure:** 
  - CartRadar now uses a `/api/serviceability` endpoint.
  - This endpoint actively pings the respective platform APIs (Zepto, Swiggy, BigBasket, BBNow) using the user's specific latitude and longitude (`resolve_store`).
  - True status (`open`, `closed`, ETA) is derived directly from the source API.
  - To prevent UI blocking, serviceability checks are bound to a strict 8-second timeout per platform, executing concurrently.

## 3. SSE Stream Reliability

The core search functionality streams results to the frontend using Server-Sent Events (SSE). 
- **Problem:** If a platform (e.g., BigBasket) blocked the Render IP via Cloudflare, or if a platform's API degraded, the sweep logic could hang indefinitely. The frontend would stay locked in the "searching" UI phase forever because it never received a termination signal.
- **Robustness Measure:**
  - **Bounded Timeouts:** The main `_sweep_flow()` in `search.py` is wrapped in an `asyncio.wait_for(timeout=90.0)`.
  - **Graceful Degradation:** Upon timeout, the backend catches the `asyncio.TimeoutError`. Instead of crashing or emitting a generic error that destroys the search state, it explicitly emits `{"type": "done", "summary": ...}`.
  - This ensures the frontend receives the closure event, stops the loading animation, and displays whatever partial results were discovered before the timeout.

## 4. Platform Isolation

- **Problem:** If one platform fails, it shouldn't break the entire application.
- **Robustness Measure:** 
  - The architecture is decentralized. Each platform logic is encapsulated in a dedicated `PlatformClient` (e.g., `zepto.py`, `bigbasket.py`). 
  - Searches are performed individually. An issue in BigBasket's client cannot bleed into the Zepto client's execution flow.
  - The `ConcurrencyGate` and `TokenBucket` rate limiters operate globally to prevent any single platform from starving backend resources or triggering wide-scale ban cascades.

## 5. UI State Resilience

- **Problem:** If a backend search completed normally but returned zero stores (due to platform WAF blocks or genuine unavailability), the frontend mistakenly persisted in a visual "Checking..." state because it only verified non-zero arrays when rendering terminal UI text.
- **Robustness Measure:**
  - The UI state machine in `App.tsx` is now strictly coupled to the SSE stream's `phase` attribute rather than the size of the results array.
  - If `state.phase === "done"`, the UI guarantees a terminal state ("No stores found") regardless of whether the results array has 100 elements or 0 elements. This prevents infinite pseudo-loading loops.

## Limitations & Risks Remaining

- **Playwright Disabled on Render:** As noted, Blinkit cannot be searched on the free Render tier due to RAM limitations. To support Blinkit, a RAM upgrade (1GB+) is required.
- **IP Blocking (Cloudflare/WAF):** Quick-commerce platforms actively block cloud provider IPs. We implemented sweep timeouts to fail fast gracefully, but legitimate searches may still yield no results when run from Render compared to localhost.
