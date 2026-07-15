"""Unified link detection and product ID extraction across all platforms.

Auto-detects which platform a URL belongs to, and extracts the product ID
without any network calls when possible.
"""

import re
from urllib.parse import parse_qs, urlparse

# -- Zepto patterns -------------------------------------------------------
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
PVID_RE = re.compile(rf"/pvid/({UUID})")
UUID_RE = re.compile(UUID)

# -- Platform host mappings ------------------------------------------------
PLATFORM_HOSTS: dict[str, tuple[str, ...]] = {
    "zepto": ("zepto.com", "zeptonow.com", "zepto.app.link"),
    "swiggy": ("swiggy.com",),
    "bigbasket": ("bigbasket.com", "bb.com", "bbdaily.com"),
    "blinkit": ("blinkit.com", "grofers.com", "blinkit.app.link"),
}

# -- Per-platform product ID regexes ----------------------------------------
# Swiggy Instamart: /instamart/item/{alphanumeric_id}
# and canonical SEO links like /instamart/p/{slug}-{alphanumeric_id}
# and share links like /stores/instamart/item/{alphanumeric_id}
SWIGGY_PRODUCT_RE = re.compile(r"/(?:stores/)?instamart/(?:item|p)/(?:.*-)?([A-Za-z0-9_-]+)(?:[/?#]|$)")
# BigBasket: /pd/{numeric_id}/{slug}/
BB_PRODUCT_RE = re.compile(r"/pd/(\d+)/")
# Blinkit: /pr/{slug}/prid/{numeric_id}
BLINKIT_PRODUCT_RE = re.compile(r"/pr(?:oduct)?/(?:.*?/prid/)?(\d+)")


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to.

    Returns 'zepto' | 'swiggy' | 'bigbasket' | 'blinkit' | None.
    """
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except ValueError:
        return None
    for platform, hosts in PLATFORM_HOSTS.items():
        if any(host == h or host.endswith("." + h) for h in hosts):
            return platform
    return None


def extract_product_id(text: str) -> tuple[str | None, str | None]:
    """Extract platform name and product ID from a URL or pasted text.

    Returns (platform, product_id) or (None, None) if not recognised.
    No network calls — pure parsing.
    """
    text = text.strip()
    platform = detect_platform(text)

    if platform == "zepto":
        pid = _extract_zepto_id(text)
        return ("zepto", pid) if pid else (None, None)
    elif platform == "swiggy":
        m = SWIGGY_PRODUCT_RE.search(text)
        return ("swiggy", m.group(1)) if m else ("swiggy", None)
    elif platform == "bigbasket":
        m = BB_PRODUCT_RE.search(text)
        return ("bigbasket", m.group(1)) if m else ("bigbasket", None)
    elif platform == "blinkit":
        m = BLINKIT_PRODUCT_RE.search(text)
        return ("blinkit", m.group(1)) if m else ("blinkit", None)

    # Not a known platform URL — try raw pvid  extraction (Zepto-style)
    pid = _extract_zepto_id(text)
    if pid:
        return ("zepto", pid)

    return (None, None)


def _extract_zepto_id(text: str) -> str | None:
    """Pull a Zepto pvid out of a URL or pasted text."""
    m = PVID_RE.search(text)
    if m:
        return m.group(1).lower()
    try:
        qs = parse_qs(urlparse(text.strip()).query)
    except ValueError:
        return None
    for values in qs.values():
        for v in values:
            m = UUID_RE.search(v)
            if m and "/pvid/" not in v:
                return m.group(0).lower()
    return None


def first_url(text: str) -> str | None:
    """Find the first http(s) URL in a pasted share blob."""
    m = re.search(r"https?://\S+", text)
    return m.group(0).rstrip(".,;)\"'") if m else None


def looks_like_product_link(text: str) -> bool:
    """Quick check: does this text contain a recognisable product link?"""
    platform = detect_platform(text)
    if platform:
        return True
    return bool(PVID_RE.search(text))
