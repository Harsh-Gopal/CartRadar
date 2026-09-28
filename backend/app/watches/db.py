"""SQLite persistence for Worth-It watches and watch events.

Uses the same database file as Cart Radar (data/mega.db) via a new schema.
All operations use synchronous sqlite3 (Cart Radar uses sync SQLite throughout).
"""

from __future__ import annotations

import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from .models import Watch, WatchEvent, VALID_INTERVALS

log = logging.getLogger("watches.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_url TEXT NOT NULL,
    product_name TEXT,
    product_image TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    radius_km REAL NOT NULL DEFAULT 10.0,
    in_stock_only INTEGER NOT NULL DEFAULT 1,
    max_price REAL,
    min_discount_pct REAL,
    interval_minutes INTEGER NOT NULL DEFAULT 15,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    last_scan_at TEXT,
    next_scan_at TEXT,
    scan_count INTEGER NOT NULL DEFAULT 0,
    found_count INTEGER NOT NULL DEFAULT 0,
    telegram_chat_id TEXT,
    notify_browser INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS watch_events (
    id TEXT PRIMARY KEY,
    watch_id TEXT NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    scanned_at TEXT NOT NULL,
    found_in_stock INTEGER NOT NULL DEFAULT 0,
    price REAL,
    mrp REAL,
    discount_pct REAL,
    store_id TEXT,
    store_name TEXT,
    store_lat REAL,
    store_lng REAL,
    distance_km REAL,
    criteria_met INTEGER NOT NULL DEFAULT 0,
    alerted_telegram INTEGER NOT NULL DEFAULT 0,
    alerted_browser INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_watch_events_watch_id ON watch_events(watch_id);
CREATE INDEX IF NOT EXISTS idx_watch_events_scanned_at ON watch_events(scanned_at);
CREATE INDEX IF NOT EXISTS idx_watches_status ON watches(status);
"""


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _row_to_watch(row: sqlite3.Row) -> Watch:
    return Watch(
        id=row["id"],
        name=row["name"],
        platform=row["platform"],
        product_id=row["product_id"],
        product_url=row["product_url"],
        product_name=row["product_name"],
        product_image=row["product_image"],
        lat=row["lat"],
        lng=row["lng"],
        radius_km=row["radius_km"],
        in_stock_only=bool(row["in_stock_only"]),
        max_price=row["max_price"],
        min_discount_pct=row["min_discount_pct"],
        interval_minutes=row["interval_minutes"],
        status=row["status"],
        created_at=_parse_dt(row["created_at"]) or datetime.utcnow(),
        last_scan_at=_parse_dt(row["last_scan_at"]),
        next_scan_at=_parse_dt(row["next_scan_at"]),
        scan_count=row["scan_count"],
        found_count=row["found_count"],
        telegram_chat_id=row["telegram_chat_id"],
        notify_browser=bool(row["notify_browser"]),
    )


def _row_to_event(row: sqlite3.Row) -> WatchEvent:
    return WatchEvent(
        id=row["id"],
        watch_id=row["watch_id"],
        scanned_at=_parse_dt(row["scanned_at"]) or datetime.utcnow(),
        found_in_stock=bool(row["found_in_stock"]),
        price=row["price"],
        mrp=row["mrp"],
        discount_pct=row["discount_pct"],
        store_id=row["store_id"],
        store_name=row["store_name"],
        store_lat=row["store_lat"],
        store_lng=row["store_lng"],
        distance_km=row["distance_km"],
        criteria_met=bool(row["criteria_met"]),
        alerted_telegram=bool(row["alerted_telegram"]),
        alerted_browser=bool(row["alerted_browser"]),
        notes=row["notes"] or "",
    )


class WatchDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        self._db.commit()
        log.info("WatchDB initialized at %s", path)

    # ── Watches ──────────────────────────────────────────────────────────────

    def create_watch(self, watch: Watch) -> Watch:
        self._db.execute(
            """INSERT INTO watches
               (id, name, platform, product_id, product_url, product_name, product_image,
                lat, lng, radius_km, in_stock_only, max_price, min_discount_pct,
                interval_minutes, status, created_at, last_scan_at, next_scan_at,
                scan_count, found_count, telegram_chat_id, notify_browser)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                watch.id, watch.name, watch.platform, watch.product_id, watch.product_url,
                watch.product_name, watch.product_image,
                watch.lat, watch.lng, watch.radius_km,
                int(watch.in_stock_only), watch.max_price, watch.min_discount_pct,
                watch.interval_minutes, watch.status,
                _fmt_dt(watch.created_at), _fmt_dt(watch.last_scan_at), _fmt_dt(watch.next_scan_at),
                watch.scan_count, watch.found_count,
                watch.telegram_chat_id, int(watch.notify_browser),
            ),
        )
        self._db.commit()
        return watch

    def get_watch(self, watch_id: str) -> Optional[Watch]:
        row = self._db.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
        return _row_to_watch(row) if row else None

    def list_watches(self) -> List[Watch]:
        rows = self._db.execute("SELECT * FROM watches ORDER BY created_at DESC").fetchall()
        return [_row_to_watch(r) for r in rows]

    def list_active_watches(self) -> List[Watch]:
        rows = self._db.execute(
            "SELECT * FROM watches WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_watch(r) for r in rows]

    def update_watch_status(self, watch_id: str, status: str) -> None:
        self._db.execute("UPDATE watches SET status=? WHERE id=?", (status, watch_id))
        self._db.commit()

    def update_watch_scan_times(
        self,
        watch_id: str,
        last_scan_at: datetime,
        next_scan_at: Optional[datetime],
        scan_count: int,
        found_count: int,
    ) -> None:
        self._db.execute(
            """UPDATE watches SET last_scan_at=?, next_scan_at=?, scan_count=?, found_count=?
               WHERE id=?""",
            (_fmt_dt(last_scan_at), _fmt_dt(next_scan_at), scan_count, found_count, watch_id),
        )
        self._db.commit()

    def update_watch(
        self,
        watch_id: str,
        name: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        max_price: Optional[float] = None,
        min_discount_pct: Optional[float] = None,
        in_stock_only: Optional[bool] = None,
        radius_km: Optional[float] = None,
        telegram_chat_id: Optional[str] = None,
        notify_browser: Optional[bool] = None,
    ) -> None:
        updates: list[str] = []
        params: list = []

        if name is not None:
            updates.append("name=?"); params.append(name)
        if interval_minutes is not None:
            updates.append("interval_minutes=?"); params.append(interval_minutes)
        if max_price is not None:
            updates.append("max_price=?"); params.append(max_price)
        if min_discount_pct is not None:
            updates.append("min_discount_pct=?"); params.append(min_discount_pct)
        if in_stock_only is not None:
            updates.append("in_stock_only=?"); params.append(int(in_stock_only))
        if radius_km is not None:
            updates.append("radius_km=?"); params.append(radius_km)
        if telegram_chat_id is not None:
            updates.append("telegram_chat_id=?"); params.append(telegram_chat_id)
        if notify_browser is not None:
            updates.append("notify_browser=?"); params.append(int(notify_browser))

        if not updates:
            return

        params.append(watch_id)
        self._db.execute(f"UPDATE watches SET {', '.join(updates)} WHERE id=?", params)
        self._db.commit()

    def delete_watch(self, watch_id: str) -> None:
        self._db.execute("DELETE FROM watches WHERE id=?", (watch_id,))
        self._db.commit()

    # ── Events ───────────────────────────────────────────────────────────────

    def create_event(self, event: WatchEvent) -> WatchEvent:
        self._db.execute(
            """INSERT INTO watch_events
               (id, watch_id, scanned_at, found_in_stock, price, mrp, discount_pct,
                store_id, store_name, store_lat, store_lng, distance_km,
                criteria_met, alerted_telegram, alerted_browser, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event.id, event.watch_id, _fmt_dt(event.scanned_at),
                int(event.found_in_stock), event.price, event.mrp, event.discount_pct,
                event.store_id, event.store_name, event.store_lat, event.store_lng, event.distance_km,
                int(event.criteria_met), int(event.alerted_telegram), int(event.alerted_browser),
                event.notes,
            ),
        )
        self._db.commit()
        return event

    def mark_event_alerted(self, event_id: str, telegram: bool = False, browser: bool = False) -> None:
        self._db.execute(
            "UPDATE watch_events SET alerted_telegram=?, alerted_browser=? WHERE id=?",
            (int(telegram), int(browser), event_id),
        )
        self._db.commit()

    def list_events(self, watch_id: str, limit: int = 50) -> List[WatchEvent]:
        rows = self._db.execute(
            "SELECT * FROM watch_events WHERE watch_id=? ORDER BY scanned_at DESC LIMIT ?",
            (watch_id, limit),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def latest_event(self, watch_id: str) -> Optional[WatchEvent]:
        row = self._db.execute(
            "SELECT * FROM watch_events WHERE watch_id=? ORDER BY scanned_at DESC LIMIT 1",
            (watch_id,),
        ).fetchone()
        return _row_to_event(row) if row else None
