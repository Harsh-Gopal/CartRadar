"""Search orchestrator: home check → store discovery sweep → per-store stock checks.

Yields SSE-ready event dicts as results arrive so the UI fills in live.
Extended to support multiple platforms through the PlatformClient interface.
"""

import asyncio
import logging
from dataclasses import asdict
from typing import AsyncIterator

from .config import GRID_SPACING_KM, PROBE_COVERAGE_KM
from .grid import haversine_km, hex_grid
from .platforms.base import PlatformClient, PlatformError
from .ratelimit import TokenBucket
from .store_cache import Store, StoreCache

log = logging.getLogger("search")


async def run_search(
    client: PlatformClient,
    cache: StoreCache,
    product_id: str,
    lat: float,
    lng: float,
    radius_km: float,
    force: bool = False,
    probe_budget: TokenBucket | None = None,
    address_resolver = None,
) -> AsyncIterator[dict]:
    """Run a stock check search using any PlatformClient.

    For platforms that support sweep (client.supports_sweep == True), this
    does the full hex-grid store discovery + per-store stock check.

    For platforms that don't support sweep yet, it does a simpler
    location-based check (product_at_location).
    """
    if client.platform_name == "zepto":
        from .platforms.zepto import run_zepto_search
        async for event in run_zepto_search(client, product_id, lat, lng, radius_km, cache, force, address_resolver):
            yield event
        return

    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    checked: set[str] = set()
    check_tasks: list[asyncio.Task] = []
    platform = client.platform_name
    counts = {"in_stock": 0, "out_of_stock": 0, "not_carried": 0, "error": 0, "stores": 0}

    async def emit(event: dict) -> None:
        # Tag every event with the platform name
        event["platform"] = platform
        await queue.put(event)

    async def check_store(store: Store) -> None:
        distance = haversine_km(lat, lng, store.lat, store.lng)
        try:
            result = await client.product_at_store(product_id, store.id, lat=store.lat, lng=store.lng)
        except PlatformError as e:
            log.warning("stock check failed for %s/%s: %s", platform, store.id, e)
            result = None
        status = result.status if result else "error"
        counts[status] = counts.get(status, 0) + 1
        await emit(
            {
                "type": "store_result",
                "store": asdict(store),
                "distance_km": round(distance, 1),
                "status": status,
                "price": result.price if result else None,
                "mrp": result.mrp if result else None,
                "product": asdict(result) if result else None,
            }
        )

    def start_check(store: Store) -> None:
        if store.id in checked:
            return
        checked.add(store.id)
        counts["stores"] += 1
        check_tasks.append(asyncio.create_task(check_store(store)))

    async def probe_point(plat: float, plng: float, progress: dict) -> None:
        try:
            res = await client.resolve_store(plat, plng, product_id=product_id)
        except PlatformError as e:
            log.warning("probe (%.4f, %.4f) failed on %s: %s", plat, plng, platform, e)
            progress["failed"] += 1
            return
        finally:
            progress["probed"] += 1
            if progress["probed"] % 5 == 0 or progress["probed"] == progress["total"]:
                await emit({"type": "discovery_progress", **progress})
                
        if res.serviceable and res.store_id:
            if platform == "flipkart_minutes":
                nearby = cache.stores_within(plat, plng, 3.0, platform)
                if nearby:
                    res.store_id = nearby[0].id
                else:
                    import time
                    res.store_id = f"fm_store_{int(time.time())}_{round(plat, 3)}_{round(plng, 3)}"

        try:
            # We don't resolve address via probe coordinates anymore. Just record the probe.
            # Record probe handles None store_ids properly too
            store = None
            if res.store_id and not res.store_id.startswith("synthetic_") and not res.store_id.startswith("fm_store_"):
                store = cache.record_probe(plat, plng, res.store_id, res.store_name, res.city, res.pincode, platform)
                # Resolve address using STORE coordinates (not probe grid point)
                if store and not (store.city and store.pincode) and address_resolver:
                    await address_resolver.resolve_for_store(store, cache)
                    # Update the store record with resolved city/pincode
                    cache.update_store_address(store.id, platform, store.city, store.pincode)

                if store:
                    start_check(store)
            else:
                cache.record_probe(plat, plng, None, None, None, None, platform)
                
            if res.secondary_store_id and not res.secondary_store_id.startswith("synthetic_") and not res.secondary_store_id.startswith("fm_store_"):
                secondary = cache.record_store(plat, plng, res.secondary_store_id, platform=platform)
                if secondary:
                    start_check(secondary)
        except Exception as e:
            log.error("Failed to record probe for store %s (platform: %s, lat/lng: %s/%s): %s", res.store_id, platform, plat, plng, e)

    async def main_flow() -> None:
        try:
            if client.supports_sweep:
                # Full sweep flow (like Zepto) — with a hard timeout so WAF blocks don't hang forever
                try:
                    await asyncio.wait_for(_sweep_flow(), timeout=90.0)
                except asyncio.TimeoutError:
                    log.warning("sweep timed out after 90s on %s — emitting done", platform)
                    await emit({"type": "done", "summary": dict(counts)})
            else:
                # Simple location check (for platforms without sweep support yet)
                await _simple_flow()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("search failed on %s", platform)
            await emit({"type": "error", "message": f"Search failed on {client.display_name} — API may be down or blocking."})
        finally:
            await queue.put(None)

    async def _sweep_flow() -> None:
        """Full hex-grid sweep flow, same as zepto-finder."""
        # 1. Home store check
        home = await client.resolve_store(lat, lng, product_id=product_id)
        home_product = None
        home_eta = home.eta_minutes
        
        if home.serviceable and home.store_id:
            # Deduplicate/cluster Flipkart Minutes points to avoid marking every grid coordinate as a unique store
            if platform == "flipkart_minutes":
                nearby = cache.stores_within(lat, lng, 3.0, platform)
                if nearby:
                    home.store_id = nearby[0].id
                else:
                    import time
                    home.store_id = f"fm_store_{int(time.time())}_{round(lat, 3)}_{round(lng, 3)}"

            checked.add(home.store_id)
            
            home_store = cache.record_probe(lat, lng, home.store_id, home.store_name, home.city, home.pincode, platform)
            
            if home_store and not (home_store.city and home_store.pincode) and address_resolver:
                await address_resolver.resolve_for_store(home_store, cache)
                cache.update_store_address(home_store.id, platform, home_store.city, home_store.pincode)
                
                # Make sure the home StoreResolution has updated city/pincode for the home_result event
                home.city = home_store.city
                home.pincode = home_store.pincode
                
            home_product = await client.product_at_store(product_id, home.store_id, lat=lat, lng=lng)
            if home.secondary_store_id and (
                home_product is None or home_product.status != "in_stock"
            ):
                checked.add(home.secondary_store_id)
                alt = await client.product_at_store(product_id, home.secondary_store_id, lat=lat, lng=lng)
                if alt.status == "in_stock":
                    home_product = alt
                    home_eta = home.secondary_eta_minutes
        else:
            cache.record_probe(lat, lng, None, None, None, platform)
        await emit(
            {
                "type": "home_result",
                "serviceable": home.serviceable,
                "city": home.city,
                "pincode": home.pincode,
                "store_name": home.store_name,
                "eta_minutes": home_eta,
                "product": asdict(home_product) if home_product else None,
            }
        )

        # Always emit a store_result for the home store so it appears in the
        # map and stores list. Without this, cities/areas with only one dark
        # store (e.g. smaller cities like Patna) show zero store_result events,
        # triggering the "Search nearby stores anyway" button — even though the
        # sweep correctly ran and found the one store via the home check.
        if home.serviceable and home.store_id and home_product and home_store:
            _home_store_entry = Store(
                id=home.store_id,
                name=home.store_name,
                city=home.city,
                pincode=home.pincode,
                lat=home_store.lat,
                lng=home_store.lng,
                platform=platform,
            )
            counts["stores"] += 1
            _h_status = home_product.status
            counts[_h_status] = counts.get(_h_status, 0) + 1
            await emit(
                {
                    "type": "store_result",
                    "store": asdict(_home_store_entry),
                    "distance_km": 0.0,
                    "status": _h_status,
                    "price": home_product.price,
                    "mrp": home_product.mrp,
                }
            )

        # 2. Stock checks for cached stores
        for store in cache.stores_within(lat, lng, radius_km, platform):
            start_check(store)

        # 3. Sweep undiscovered area (or ALL area when force=True for re-check)
        if force:
            # Force re-check: probe all grid points regardless of cache freshness.
            # This ensures Re-check stock returns real-time data, not stale probes.
            undiscovered = list(hex_grid(lat, lng, radius_km, GRID_SPACING_KM))
        else:
            undiscovered = [
                p
                for p in hex_grid(lat, lng, radius_km, GRID_SPACING_KM)
                if not cache.has_fresh_probe_near(p[0], p[1], PROBE_COVERAGE_KM, platform)
            ]
        if probe_budget is not None:
            granted = probe_budget.take_up_to(len(undiscovered))
        else:
            granted = len(undiscovered)
        to_probe = undiscovered[:granted]
        budget_limited = granted < len(undiscovered)

        progress = {"probed": 0, "failed": 0, "total": len(to_probe)}
        await emit(
            {
                "type": "discovery_start",
                "points_to_probe": len(to_probe),
                "cached_stores": counts["stores"],
            }
        )
        if budget_limited:
            log.warning("probe budget limited sweep: %d/%d points", granted, len(undiscovered))
            await emit(
                {
                    "type": "notice",
                    "message": "Daily store-mapping limit reached — some far stores may be missing.",
                }
            )
        if to_probe:
            await asyncio.gather(*(probe_point(p[0], p[1], progress) for p in to_probe))
        await emit({"type": "checking", "total_stores": counts["stores"]})
        if check_tasks:
            await asyncio.gather(*check_tasks)
        await emit({"type": "done", "summary": dict(counts)})

    async def _simple_flow() -> None:
        """Simple per-location check for platforms without sweep support."""
        await emit({"type": "discovery_start", "points_to_probe": 0, "cached_stores": 0})
        try:
            result = await client.product_at_location(product_id, lat, lng)
            status = result.status
            counts[status] = counts.get(status, 0) + 1
            counts["stores"] = 1
            await emit(
                {
                    "type": "home_result",
                    "serviceable": status != "not_carried",
                    "city": None,
                    "pincode": None,
                    "store_name": f"{client.display_name} (your location)",
                    "eta_minutes": None,
                    "product": asdict(result),
                }
            )
        except PlatformError as e:
            log.warning("simple check failed on %s: %s", platform, e)
            await emit(
                {
                    "type": "home_result",
                    "serviceable": False,
                    "city": None,
                    "pincode": None,
                    "store_name": None,
                    "eta_minutes": None,
                    "product": None,
                }
            )
            await emit({"type": "error", "message": f"{client.display_name}: {e}"})
        await emit({"type": "done", "summary": dict(counts)})

    flow = asyncio.create_task(main_flow())
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        flow.cancel()
        for t in check_tasks:
            t.cancel()
