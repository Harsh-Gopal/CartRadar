"""
Worth-It background scheduler.

Uses APScheduler's AsyncIOScheduler (not a 30-second loop).
Each watch gets its own APScheduler job that fires at the watch's configured interval.

Scan logic:
  1. Use Cart Radar's existing run_search() generator with the watch's platform + product_id
  2. Collect store_result events where status=in_stock
  3. Evaluate deal criteria from the watch config
  4. Persist WatchEvent with best qualifying result (nearest in-stock store)
  5. If criteria_met and not already alerted in this cycle → send Telegram alert
  6. Emit all lifecycle events to the watch's SSE console ring buffer

Resource management:
  - Max 2 concurrent scan tasks (asyncio.Semaphore)
  - Per-watch APScheduler job (not a global loop)
  - Shared httpx.AsyncClient (not one per scan)
  - No Playwright required for background scans (Swiggy uses httpx-only path)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..search import run_search
from .models import Watch, WatchEvent, VALID_INTERVALS
from .db import WatchDB
from .console import emit_log, get_console
from .telegram import send_watch_alert

log = logging.getLogger("watches.scheduler")

_scheduler: Optional[AsyncIOScheduler] = None
_scan_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)  # max 2 concurrent scans
_db: Optional[WatchDB] = None
_clients: Optional[dict] = None  # Cart Radar platform clients from app.state

JOB_PREFIX = "watch_"


def init_scheduler(db: WatchDB, clients: dict) -> AsyncIOScheduler:
    """Initialize and return the APScheduler instance. Call once in lifespan."""
    global _scheduler, _db, _clients

    _db = db
    _clients = clients

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.start()
    log.info("Watch scheduler started")

    # Schedule all currently active watches
    watches = db.list_active_watches()
    for watch in watches:
        _schedule_watch(watch)
    log.info("Scheduled %d existing active watches", len(watches))

    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Watch scheduler stopped")


def _schedule_watch(watch: Watch) -> None:
    """Add or replace the APScheduler job for a watch."""
    if _scheduler is None:
        return
    interval = watch.interval_minutes if watch.interval_minutes in VALID_INTERVALS else 15
    job_id = f"{JOB_PREFIX}{watch.id}"
    _scheduler.add_job(
        _run_scan_job,
        trigger=IntervalTrigger(minutes=interval),
        id=job_id,
        name=f"Watch: {watch.name}",
        args=[watch.id],
        replace_existing=True,
        misfire_grace_time=60,  # allow 60s late start
    )
    log.info("Scheduled watch %s (%s) every %d min", watch.id, watch.name, interval)


def _unschedule_watch(watch_id: str) -> None:
    """Remove the APScheduler job for a watch."""
    if _scheduler is None:
        return
    job_id = f"{JOB_PREFIX}{watch_id}"
    try:
        _scheduler.remove_job(job_id)
        log.info("Removed schedule for watch %s", watch_id)
    except Exception:
        pass


def schedule_new_watch(watch: Watch) -> None:
    """Called when a watch is created. Adds scheduler job immediately."""
    _schedule_watch(watch)


def unschedule_watch(watch_id: str) -> None:
    """Called when a watch is deleted or paused."""
    _unschedule_watch(watch_id)


def reschedule_watch(watch: Watch) -> None:
    """Called when interval or status changes."""
    if watch.status == "active":
        _schedule_watch(watch)
    else:
        _unschedule_watch(watch.id)


async def trigger_scan_now(watch_id: str) -> Optional[WatchEvent]:
    """
    Trigger an immediate scan for a watch (e.g. from UI 'Scan Now' button).
    Returns the created WatchEvent or None.
    """
    return await _run_scan(watch_id)


async def _run_scan_job(watch_id: str) -> None:
    """APScheduler job entry point — wraps _run_scan."""
    await _run_scan(watch_id)


async def _run_scan(watch_id: str) -> Optional[WatchEvent]:
    """Execute a single scan cycle for a watch."""
    global _db, _clients

    if _db is None or _clients is None:
        log.error("Scheduler not initialized")
        return None

    watch = _db.get_watch(watch_id)
    if not watch:
        log.warning("Watch %s not found — removing job", watch_id)
        _unschedule_watch(watch_id)
        return None

    if watch.status != "active":
        log.debug("Watch %s is %s — skipping scan", watch_id, watch.status)
        return None

    client = _clients.get(watch.platform)
    if not client:
        emit_log(watch_id, "error", f"Platform '{watch.platform}' not available — scan skipped")
        return None

    # Acquire concurrency slot
    async with _scan_semaphore:
        return await _do_scan(watch, client)


async def _do_scan(watch: Watch, client) -> Optional[WatchEvent]:
    """The actual scan: run Cart Radar search, evaluate criteria, persist + alert."""
    watch_id = watch.id
    now = datetime.now(timezone.utc)

    emit_log(watch_id, "info", f"▶ Scan started for: {watch.name}")
    emit_log(watch_id, "info", f"  Platform: {watch.platform} | Product: {watch.product_id}")
    emit_log(watch_id, "info", f"  Radius: {watch.radius_km}km | Location: ({watch.lat:.4f}, {watch.lng:.4f})")

    # Use Cart Radar's store cache
    from ..store_cache import StoreCache
    from .. import config
    store_cache = StoreCache(config.DATABASE_PATH)

    best_result: Optional[dict] = None
    stores_found = 0
    in_stock_count = 0

    try:
        async for event in run_search(
            client=client,
            cache=store_cache,
            product_id=watch.product_id,
            lat=watch.lat,
            lng=watch.lng,
            radius_km=watch.radius_km,
            force=False,
            probe_budget=None,  # no budget limit for background scans
        ):
            etype = event.get("type", "")

            if etype == "store_result":
                stores_found += 1
                status = event.get("status", "")
                dist = event.get("distance_km", 0.0)
                store = event.get("store", {})
                price = event.get("price")
                mrp = event.get("mrp")
                discount = ((mrp - price) / mrp * 100) if (price and mrp and mrp > price) else 0.0

                emit_log(watch_id, "debug",
                    f"  Store: {store.get('name', store.get('id', '?'))} — "
                    f"{status} @ ₹{price or '?'} ({dist:.1f}km)")

                if status == "in_stock":
                    in_stock_count += 1
                    # Track best result (nearest in-stock store)
                    if best_result is None or dist < best_result.get("distance_km", 999):
                        best_result = {
                            "price": price,
                            "mrp": mrp,
                            "discount_pct": round(discount, 1),
                            "store_id": store.get("id"),
                            "store_name": store.get("name"),
                            "store_lat": store.get("lat"),
                            "store_lng": store.get("lng"),
                            "distance_km": dist,
                        }

            elif etype == "done":
                summary = event.get("summary", {})
                emit_log(watch_id, "info",
                    f"  ✓ Scan done — {stores_found} stores checked, "
                    f"{in_stock_count} in stock, "
                    f"out_of_stock={summary.get('out_of_stock', 0)}")

            elif etype == "error":
                emit_log(watch_id, "error", f"  ✗ {event.get('message', 'scan error')}")

    except asyncio.CancelledError:
        emit_log(watch_id, "warn", "  Scan cancelled")
        raise
    except Exception as e:
        emit_log(watch_id, "error", f"  Scan exception: {e}")
        log.exception("Scan failed for watch %s", watch_id)

    # Evaluate deal criteria
    found_in_stock = best_result is not None
    criteria_met = False

    if found_in_stock and best_result:
        criteria_met = True  # start with True, then apply filters

        if watch.in_stock_only and not found_in_stock:
            criteria_met = False

        price = best_result.get("price")
        if watch.max_price is not None and price is not None:
            if price > watch.max_price:
                criteria_met = False
                emit_log(watch_id, "info",
                    f"  Price ₹{price:.0f} > max ₹{watch.max_price:.0f} — criteria not met")

        discount = best_result.get("discount_pct", 0.0)
        if watch.min_discount_pct is not None:
            if discount < watch.min_discount_pct:
                criteria_met = False
                emit_log(watch_id, "info",
                    f"  Discount {discount:.0f}% < min {watch.min_discount_pct:.0f}% — criteria not met")

        if criteria_met:
            emit_log(watch_id, "success",
                f"  🎉 Criteria MET: ₹{price:.0f} | {discount:.0f}% off | "
                f"{best_result.get('store_name', '?')} @ {best_result.get('distance_km', 0):.1f}km")
        else:
            emit_log(watch_id, "info", "  Criteria not met for this scan")
    else:
        emit_log(watch_id, "info", "  No in-stock results found")

    # Build notes string
    notes = ""
    if best_result:
        price = best_result.get("price")
        discount = best_result.get("discount_pct", 0.0)
        store_name = best_result.get("store_name", "")
        dist = best_result.get("distance_km", 0.0)
        notes_parts = []
        if price:
            notes_parts.append(f"₹{price:.0f}")
        if discount:
            notes_parts.append(f"{discount:.0f}% off")
        if store_name:
            notes_parts.append(f"at {store_name}")
        if dist:
            notes_parts.append(f"{dist:.1f}km")
        notes = " — ".join(notes_parts)

    # Persist event
    event_id = str(uuid.uuid4())
    watch_event = WatchEvent(
        id=event_id,
        watch_id=watch_id,
        scanned_at=now,
        found_in_stock=found_in_stock,
        price=best_result.get("price") if best_result else None,
        mrp=best_result.get("mrp") if best_result else None,
        discount_pct=best_result.get("discount_pct") if best_result else None,
        store_id=best_result.get("store_id") if best_result else None,
        store_name=best_result.get("store_name") if best_result else None,
        store_lat=best_result.get("store_lat") if best_result else None,
        store_lng=best_result.get("store_lng") if best_result else None,
        distance_km=best_result.get("distance_km") if best_result else None,
        criteria_met=criteria_met,
        notes=notes,
    )
    _db.create_event(watch_event)

    # Update watch scan metadata
    new_scan_count = watch.scan_count + 1
    new_found_count = watch.found_count + (1 if criteria_met else 0)
    next_scan = datetime.now(timezone.utc) + timedelta(minutes=watch.interval_minutes)
    _db.update_watch_scan_times(watch_id, now, next_scan, new_scan_count, new_found_count)

    # Send Telegram alert if criteria met
    if criteria_met:
        alerted = await send_watch_alert(watch, watch_event)
        if alerted:
            _db.mark_event_alerted(event_id, telegram=True)
            emit_log(watch_id, "success", "  📱 Telegram alert sent")
        else:
            emit_log(watch_id, "warn", "  📱 Telegram not configured or failed")

    emit_log(watch_id, "info", f"◀ Scan complete. Next scan in {watch.interval_minutes}min")
    return watch_event
