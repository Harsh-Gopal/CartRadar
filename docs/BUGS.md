# Cart Radar Bug Tracker

This document tracks all bugs discovered during the end-to-end architectural, security, and functional audit of the Cart Radar project.

## Critical

### 1. [Open] Swiggy Instamart Pincode Serviceability Check Failing (Partially Fixed)
- **Reproduction Steps**: Search for `https://www.swiggy.com/stores/instamart/item/F9UK3KLPCI` in Patna (800014).
- **Expected vs Actual**: Expected to show the item availability correctly. Instead, it was returning "not available" for an item that is available in that pincode.
- **Root Cause (if known)**: Areas with only one dark store (e.g. smaller cities like Patna) were missing a `store_result` event because the sweep flow didn't emit it correctly for the home store.
- **Affected Files**: `backend/app/search.py`
- **Recommended Fix**: Forced emission of `store_result` for the home store is implemented. Needs further validation across different locations.
- **Notes**: Initially fixed, but user reported intermittent issues remaining. Testing Zepto search flow in other areas is needed.

### 2. [Open] Zepto Location Search Failing
- **Reproduction Steps**: Type a location in the search bar.
- **Expected vs Actual**: Expected location suggestions. Actual is no suggestions or errors during search.
- **Root Cause (if known)**: Unknown. Needs investigation.
- **Affected Files**: TBD
- **Recommended Fix**: TBD
- **Notes**: Reported by user.

## High

## Medium

### 1. [Open] `pytest` failing due to hardcoded virtual environment paths
- **Reproduction Steps**: Run `pytest tests/` in the `backend/` directory.
- **Expected vs Actual**: Tests run successfully. Actual was an error because the `pytest` executable's shebang contained an old path (`mega-finder` instead of `cart-radar`).
- **Root Cause (if known)**: The project folder was renamed from `mega-finder` to `cart-radar`, breaking the `uv` virtual environment.
- **Affected Files**: `backend/.venv/bin/*`
- **Recommended Fix**: Recreate the virtual environment using `rm -rf .venv && uv sync --group dev`.
- **Notes**: Fixed locally in my environment, but the bug is noted here as an operational issue.

## Low

