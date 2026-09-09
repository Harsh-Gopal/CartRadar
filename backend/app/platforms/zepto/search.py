import asyncio
import logging
from typing import AsyncIterator

from .client import ZeptoClient, ZeptoPlaywrightSession, ZeptoWafBlockedError, ZeptoNetworkError
from ..base import PlatformError
from ...grid import hex_grid
from ...store_cache import StoreCache
from ...config import GRID_SPACING_KM, PROBE_COVERAGE_KM

log = logging.getLogger("zepto_search")

async def run_zepto_search(
    client: ZeptoClient,
    pvid: str,
    lat: float,
    lng: float,
    radius_km: float,
    cache: StoreCache,
    force: bool = False,
) -> AsyncIterator[dict]:
    """Hex-grid search orchestrator for Zepto using a single Playwright session."""
    
    counts = {"stores": 0, "in_stock": 0, "out_of_stock": 0, "not_carried": 0, "error": 0, "not_serviceable": 0}
    checked_stores = set()
    
    async def emit(event: dict) -> None:
        pass # Will be overridden by the wrapper or we can just yield directly
        
    try:
        async with ZeptoPlaywrightSession() as session:
            # 1. Check Home Point First
            try:
                home_res = await session.probe_location(lat, lng)
            except Exception as e:
                log.warning(f"Zepto home probe failed: {e}")
                home_res = None
                
            home_product = None
            if home_res and home_res.get("serviceable") and home_res.get("all_store_ids"):
                for s_id in home_res["all_store_ids"]:
                    cache.record_probe(lat, lng, s_id, home_res.get("store_name"), home_res.get("city"), "zepto")
                    store_obj = cache.record_store(lat, lng, s_id, platform="zepto")
                    
                    if store_obj and store_obj.id not in checked_stores:
                        checked_stores.add(store_obj.id)
                        try:
                            prod = await session.check_product(store_obj.id, pvid)
                            status = prod.status
                            counts[status] = counts.get(status, 0) + 1
                            counts["stores"] += 1
                            
                            from ...grid import haversine_km
                            dist = haversine_km(lat, lng, store_obj.lat, store_obj.lng)
                            
                            is_verified_home = store_obj.id == home_res.get("store_id")
                            if is_verified_home:
                                home_product = prod
                            
                            yield {
                                "type": "store_result",
                                "store": {
                                    "id": store_obj.id,
                                    "name": store_obj.name,
                                    "city": store_obj.city,
                                    "lat": store_obj.lat,
                                    "lng": store_obj.lng,
                                    "platform": "zepto"
                                },
                                "distance_km": dist,
                                "status": status,
                                "price": prod.price,
                                "mrp": prod.mrp,
                                "verified": is_verified_home,
                            }
                        except Exception as e:
                            log.warning(f"Zepto product fetch failed for store {store_obj.id}: {e}")
            else:
                cache.record_probe(lat, lng, None, None, None, "zepto")
                
            yield {
                "type": "home_result",
                "serviceable": home_res.get("serviceable") if home_res else False,
                "city": home_res.get("city") if home_res else None,
                "store_name": home_res.get("store_name") if home_res else None,
                "eta_minutes": home_res.get("eta_minutes") if home_res else None,
                "product": {"status": home_product.status} if home_product else None,
            }

            # 2. Check Cached Stores in Radius
            cached_stores = cache.stores_within(lat, lng, radius_km, "zepto")
            for c_store in cached_stores:
                if c_store.id in checked_stores:
                    continue
                checked_stores.add(c_store.id)
                counts["stores"] += 1
                try:
                    prod = await session.check_product(c_store.id, pvid)
                    status = prod.status
                    counts[status] = counts.get(status, 0) + 1
                    
                    from ...grid import haversine_km
                    dist = haversine_km(lat, lng, c_store.lat, c_store.lng)
                    
                    yield {
                        "type": "store_result",
                        "store": {
                            "id": c_store.id,
                            "name": c_store.name,
                            "city": c_store.city,
                            "lat": c_store.lat,
                            "lng": c_store.lng,
                            "platform": "zepto"
                        },
                        "distance_km": dist,
                        "status": status,
                        "price": prod.price,
                        "mrp": prod.mrp,
                        "verified": False,
                    }
                except Exception as e:
                    log.warning(f"Zepto cached store fetch failed: {e}")

            # 3. Sweep Undiscovered Grid Points
            undiscovered = [
                p for p in hex_grid(lat, lng, radius_km, GRID_SPACING_KM)
                if not cache.has_fresh_probe_near(p[0], p[1], PROBE_COVERAGE_KM, "zepto")
            ]
            
            yield {
                "type": "discovery_start",
                "points_to_probe": len(undiscovered),
                "cached_stores": counts["stores"],
            }
            
            probed = 0
            failed = 0
            
            async def _probe_point(p_lat, p_lng):
                nonlocal probed, failed
                try:
                    res = await session.fast_sweep(p_lat, p_lng)
                    return (p_lat, p_lng, res)
                except Exception as e:
                    log.warning(f"Zepto fast_sweep failed at {p_lat}, {p_lng}: {e}")
                    failed += 1
                    return (p_lat, p_lng, None)

            # Fire all probes concurrently (httpx can easily handle 40 concurrent HEAD requests)
            tasks = [asyncio.create_task(_probe_point(p_lat, p_lng)) for p_lat, p_lng in undiscovered]
            
            for coro in asyncio.as_completed(tasks):
                p_lat, p_lng, res = await coro
                
                probed += 1
                if probed % 3 == 0 or probed == len(undiscovered):
                    yield {
                        "type": "discovery_progress",
                        "probed": probed,
                        "failed": failed,
                        "total": len(undiscovered)
                    }
                
                if res and res.get("serviceable") and res.get("all_store_ids"):
                    for s_id in res["all_store_ids"]:
                        new_store = cache.record_probe(p_lat, p_lng, s_id, res.get("store_name"), res.get("city"), "zepto")
                        if new_store and new_store.id not in checked_stores:
                            checked_stores.add(new_store.id)
                            counts["stores"] += 1
                            try:
                                prod = await session.check_product(new_store.id, pvid)
                                status = prod.status
                                counts[status] = counts.get(status, 0) + 1
                                
                                from ...grid import haversine_km
                                dist = haversine_km(lat, lng, new_store.lat, new_store.lng)
                                
                                yield {
                                    "type": "store_result",
                                    "store": {
                                        "id": new_store.id,
                                        "name": new_store.name,
                                        "city": new_store.city,
                                        "lat": new_store.lat,
                                        "lng": new_store.lng,
                                        "platform": "zepto"
                                    },
                                    "distance_km": dist,
                                    "status": status,
                                    "price": prod.price,
                                    "mrp": prod.mrp,
                                    "verified": False,
                                }
                            except Exception as e:
                                log.warning(f"Zepto product fetch failed for discovered store {new_store.id}: {e}")
                else:
                    cache.record_probe(p_lat, p_lng, None, None, None, "zepto")

            yield {"type": "checking", "total_stores": counts["stores"]}
            yield {"type": "done", "summary": dict(counts)}
            
    except ZeptoWafBlockedError as e:
        log.warning(f"Zepto sweep completely blocked by WAF: {e}")
        yield {"type": "error", "message": "Zepto is currently blocking access. Please try again later."}
    except Exception as e:
        log.exception("Zepto sweep failed unexpectedly")
        yield {"type": "error", "message": f"Zepto search failed: {e}"}
