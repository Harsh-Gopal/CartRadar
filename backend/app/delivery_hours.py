"""Delivery hours data for quick-commerce platforms.

Each platform has per-slot delivery hours. This is the platform's *general*
delivery window. Actual serviceability at any specific pincode may differ —
some stores run 24×7, others have cut-off hours. The frontend shows this as
a best-effort guide, NOT a guarantee.

Data sourced from platform apps, press releases, and user reports (2026).
"""

from __future__ import annotations
import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


# -- Data -------------------------------------------------------------------
# Structure:
#   platform_name -> {
#       "default": (open_hour, close_hour) in 24h IST
#       "notes": str (human-readable caveats)
#       "24x7_cities": list of city keywords for 24×7 delivery zones
#   }
#
# None for close_hour means midnight (end of day).
# 24×7 means open_hour=0, close_hour=24 (we treat this as always open).

DELIVERY_HOURS: dict[str, dict] = {
    "zepto": {
        "label": "Zepto",
        "default_open": 0,   # 12:00 AM
        "default_close": 24, # 12:00 AM next day (24×7)
        "always_open": True,
        "notes": "Zepto operates 24×7 in most metro areas. In some Tier-2 cities delivery stops around 11 PM.",
        "cities_24x7": ["mumbai", "delhi", "bangalore", "bengaluru", "hyderabad",
                         "pune", "chennai", "kolkata", "ahmedabad", "jaipur"],
    },
    "swiggy": {
        "label": "Swiggy Instamart",
        "default_open": 7,   # 7:00 AM
        "default_close": 24, # 12:00 AM next day (effectively 24×7 in many cities)
        "always_open": False,
        "notes": "Instamart is generally available from ~7 AM to midnight. 24×7 is live in Mumbai, Delhi, Bangalore and Hyderabad.",
        "cities_24x7": ["mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "pune", "chennai"],
    },
    "blinkit": {
        "label": "Blinkit",
        "default_open": 0,
        "default_close": 24,
        "always_open": True,
        "notes": "Blinkit operates 24×7 across most major cities. In smaller towns it may stop around 11 PM.",
        "cities_24x7": ["mumbai", "delhi", "ncr", "gurgaon", "noida", "bangalore",
                         "bengaluru", "hyderabad", "pune", "chennai", "kolkata",
                         "ahmedabad", "chandigarh", "jaipur", "lucknow", "surat"],
    },
    "bigbasket": {
        "label": "BigBasket",
        "default_open": 6,   # 6:00 AM
        "default_close": 23, # 11:00 PM
        "always_open": False,
        "notes": "BigBasket Now (quick delivery) typically operates 6 AM – 11 PM. Standard BB slots run all day.",
        "cities_24x7": [],
    },
    "bbnow": {
        "label": "BB Now",
        "default_open": 6,
        "default_close": 23,
        "always_open": False,
        "notes": "BB Now (quick delivery) typically operates 6 AM – 11 PM.",
        "cities_24x7": [],
    },
}


def get_delivery_status(platform: str, city: str | None = None) -> dict:
    """Return the current delivery status for a platform.
    
    Returns a dict with:
        - is_open: bool
        - opens_at: str (HH:MM IST) or None
        - closes_at: str (HH:MM IST) or None
        - always_open: bool
        - notes: str
        - label: str
    """
    now = datetime.datetime.now(tz=IST)
    hour_now = now.hour + now.minute / 60  # e.g. 23.5 = 11:30 PM

    info = DELIVERY_HOURS.get(platform)
    if not info:
        return {
            "is_open": None,  # Unknown platform
            "always_open": False,
            "opens_at": None,
            "closes_at": None,
            "notes": "Delivery hours unknown for this platform.",
            "label": platform.title(),
        }

    # Check if city is in the 24×7 city list
    city_lower = (city or "").lower()
    is_24x7_city = info["always_open"] or any(c in city_lower for c in info["cities_24x7"])

    open_h = info["default_open"]
    close_h = info["default_close"]  # 24 means closes at midnight (end of day)

    if is_24x7_city:
        is_open = True
        opens_at = None
        closes_at = None
        always_open = True
    elif close_h >= 24:
        # Closes at/past midnight — open from open_h until end of day
        is_open = hour_now >= open_h
        opens_at = f"{open_h:02d}:00" if open_h > 0 else None
        closes_at = "00:00 (next day)"
        always_open = False
    else:
        is_open = open_h <= hour_now < close_h
        opens_at = f"{open_h:02d}:00"
        closes_at = f"{close_h:02d}:00"
        always_open = False

    return {
        "is_open": is_open,
        "always_open": always_open,
        "opens_at": opens_at,
        "closes_at": closes_at,
        "notes": info["notes"],
        "label": info["label"],
    }


def get_all_delivery_status(city: str | None = None) -> dict[str, dict]:
    """Return delivery status for all platforms."""
    return {platform: get_delivery_status(platform, city) for platform in DELIVERY_HOURS}
