# Cart Radar Final Report - SQL Audit & Crash Prevention

## 1. Exact root cause
The crash `sqlite3.OperationalError: 9 values for 10 columns` occurred during `_upsert_store()` inside `backend/app/store_cache.py`. The SQL `INSERT` statement declared 10 columns (`id`, `platform`, `name`, `city`, `pincode`, `lat`, `lng`, `probe_count`, `discovered_at`, `last_seen_at`), but the `VALUES` clause only contained 9 items: `VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)`. Specifically, one `?` placeholder was missing between `lng` and the hardcoded `1` (for `probe_count`), causing a misalignment and throwing the SQLite OperationalError.

## 2. Exact SQL/schema mismatch
* **Old SQL:** `INSERT INTO stores (id, platform, name, city, pincode, lat, lng, probe_count, discovered_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)` (10 columns, 9 values)
* **New SQL:** `INSERT INTO stores (id, platform, name, city, pincode, lat, lng, probe_count, discovered_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)` (10 columns, 10 values - 9 dynamic `?` and 1 hardcoded)

## 3. Exact files changed
* `backend/app/store_cache.py`: Fixed the missing placeholder in `_upsert_store`. 
* `backend/app/search.py`: Wrapped the cache probe/store insertions in `probe_point()` with a `try...except` block so that a single database failure won't bring down the entire `asyncio.gather()` geographic sweep.
* `backend/tests/test_store_cache_regression.py`: Created from scratch to implement 5 strict regression tests enforcing StoreCache integrity.

## 4. Whether the previous pincode fix remains intact
Yes, it is entirely intact. Pincode data correctly maps to the dedicated `pincode` schema column in `_upsert_store` and propagates upwards to `StoreResult`. None of this was bypassed, and test cases now enforce its correct storage and nullability when missing. 

## 5. Whether save_address() was audited/fixed
Yes, I verified the prior `save_address()` fix. It correctly maps 8 columns (`lat`, `lng`, `formatted_address`, `short_address`, `confidence`, `provider`, `pincode`, `resolved_at`) to 8 `?` placeholders. I also added a dedicated test `test_d_address_cache` to prove `save_address` successfully persists the address without crashing.

## 6. Whether geographic store isolation remains intact
Yes. Store discovery relies on probing points (`probed_points`), and stores are bound geographically by `stores_within()`. A regression test (`test_f_geographic_isolation`) explicitly validates that out-of-range stores (relative to discovery points) are successfully filtered out. The SQL correction does not interfere with coordinate persistence or isolation.

## 7. Tests added
Added a dedicated regression suite `backend/tests/test_store_cache_regression.py` containing:
* `test_a_new_store_insert`: Proves 10-column inserts work properly without exceptions.
* `test_b_existing_store_update`: Validates `probe_count` increments correctly without overwriting authoritative lat/lng data. 
* `test_c_missing_pincode`: Confirms `None` pincodes are safely stored.
* `test_d_address_cache`: Validates address serialization and fetch logic.
* `test_f_geographic_isolation`: Verifies that radius isolation via `probed_points` remains operational.

## 8. Existing tests run
Ran `uv run pytest tests/` spanning:
* `test_links.py`
* `test_local_dev_limits.py`
* `test_store_cache_regression.py`
* `test_watches.py`

## 9. Actual test results
All tests successfully passed (`30 passed, 1 warning in 0.34s`). The `sqlite3.OperationalError` bug is 100% reproducible on the old commit and 100% fixed on the current commit. 

## 10. Build/typecheck results
The frontend builds cleanly (`tsc -b && vite build` completes successfully). 

## 11. Any remaining limitation
None detected regarding the database schema. SQLite's auto-commit overhead was previously mitigated by WAL mode and transaction scopes, which are still operating. Sweep speed is unimpacted.
