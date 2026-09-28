"""Watch models for Worth-It persistent monitoring layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


VALID_INTERVALS = (5, 15, 30)  # minutes — the only allowed scan intervals


@dataclass
class Watch:
    id: str
    name: str
    platform: str          # zepto | swiggy | bigbasket | blinkit | bbnow | flipkart | flipkart_minutes
    product_id: str        # platform-native product ID extracted from URL
    product_url: str       # original URL pasted by user
    product_name: Optional[str]
    product_image: Optional[str]

    lat: float
    lng: float
    radius_km: float       # 1–30 km

    # Deal criteria (None = not set / don't filter)
    in_stock_only: bool = True
    max_price: Optional[float] = None
    min_discount_pct: Optional[float] = None

    # Scheduling
    interval_minutes: int = 15  # must be 5, 15, or 30

    # State
    status: str = "active"     # active | paused
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_scan_at: Optional[datetime] = None
    next_scan_at: Optional[datetime] = None
    scan_count: int = 0
    found_count: int = 0       # scan cycles where at least one result met criteria

    # Notifications
    telegram_chat_id: Optional[str] = None
    notify_browser: bool = True


@dataclass
class WatchEvent:
    """A single scan result for a watch."""
    id: str
    watch_id: str
    scanned_at: datetime

    # What was found (best result, i.e. nearest in-stock or cheapest)
    found_in_stock: bool
    price: Optional[float]
    mrp: Optional[float]
    discount_pct: Optional[float]

    # Where it was found
    store_id: Optional[str]
    store_name: Optional[str]
    store_lat: Optional[float]
    store_lng: Optional[float]
    distance_km: Optional[float]

    # Deal evaluation outcome
    criteria_met: bool = False    # True if this event meets all configured criteria
    alerted_telegram: bool = False
    alerted_browser: bool = False
    notes: str = ""               # human-readable reason (e.g. "₹249 — 38% off at 1.2km")
