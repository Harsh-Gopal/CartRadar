import os
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


PROXY_URL = os.environ.get("PROXY_URL") or None
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "data/mega.db"))
ZEPTO_CONCURRENCY = int(os.environ.get("ZEPTO_CONCURRENCY", "5"))
SWIGGY_CONCURRENCY = int(os.environ.get("SWIGGY_CONCURRENCY", "5"))
BB_CONCURRENCY = int(os.environ.get("BB_CONCURRENCY", "5"))
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))

# -- abuse controls --------------------------------------------------------
DEV_MODE = _flag("DEV_MODE", False)
APP_TOKEN = os.environ.get("APP_TOKEN") or None
TRUST_FORWARDED_FOR = _flag("TRUST_FORWARDED_FOR", True)

REQUEST_BURST = int(os.environ.get("REQUEST_BURST", "30"))
REQUESTS_PER_MIN = int(os.environ.get("REQUESTS_PER_MIN", "60"))
SEARCH_BURST = int(os.environ.get("SEARCH_BURST", "1000"))
SEARCHES_PER_DAY = int(os.environ.get("SEARCHES_PER_DAY", "10000"))
MAX_CONCURRENT_SEARCHES = int(os.environ.get("MAX_CONCURRENT_SEARCHES", "3"))
GLOBAL_SEARCH_BURST = int(os.environ.get("GLOBAL_SEARCH_BURST", "1000"))
GLOBAL_SEARCHES_PER_DAY = int(os.environ.get("GLOBAL_SEARCHES_PER_DAY", "10000"))
PROBE_BURST = int(os.environ.get("PROBE_BURST", "400"))
PROBES_PER_DAY = int(os.environ.get("PROBES_PER_DAY", "3000"))

MAX_RADIUS_KM = float(os.environ.get("MAX_RADIUS_KM", "50" if DEV_MODE else "30"))
GRID_SPACING_KM = 3.0
PROBE_COVERAGE_KM = 2.0
SERVICEABLE_PROBE_TTL_DAYS = 90
UNSERVICEABLE_PROBE_TTL_DAYS = 30

# -- enabled platforms ------------------------------------------------------
# Comma-separated list of platforms to enable. Default: zepto only until
# others are implemented. Set to "zepto,swiggy,bigbasket,blinkit" to enable all.
ENABLED_PLATFORMS = [
    p.strip()
    for p in os.environ.get("ENABLED_PLATFORMS", "zepto,swiggy,bigbasket,blinkit,bbnow").split(",")
    if p.strip()
]
