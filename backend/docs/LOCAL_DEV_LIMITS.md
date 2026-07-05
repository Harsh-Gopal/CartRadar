# Local Search Limits

## Root Cause

The backend ships with production-style abuse controls in `backend/app/config.py` and `backend/app/main.py`:

- `SEARCH_BURST` defaults to `3`
- `SEARCHES_PER_DAY` defaults to `30`
- `GLOBAL_SEARCHES_PER_DAY` defaults to `500`
- those limits are only bypassed when `DEV_MODE=1`

That meant a normal localhost browser session could hit the search cap after only a few searches if the backend was started directly from an IDE, `uvicorn`, or any workflow that did not set `DEV_MODE`. The UI then surfaced the SSE error `You've reached your search limit. Try again later.` even though the app was running locally.

## Fix

Local requests are now treated as unmetered when the request host is loopback or localhost. That applies to:

- the general request limiter used by `/api/config` and other gated routes
- the `/api/search` concurrency gate
- the per-client search bucket
- the daily global search bucket
- the probe budget passed into the search engine

In practice, requests from `localhost`, `127.0.0.1`, or `::1` no longer consume the production-style budgets during local development.

## Verification

- Added a regression test that calls `/api/search` from a localhost base URL and confirms the limiter path is skipped.
- Kept `DEV_MODE=1` in `dev.sh`, so the explicit development script still works as before.

## Notes

If you want the production-style budgets back on localhost for a specific debugging session, start the backend from a non-loopback host or disable the localhost bypass in `backend/app/main.py`.
