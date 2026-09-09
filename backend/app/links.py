"""Unified link detection and product ID extraction across all platforms.

Auto-detects which platform a URL belongs to, and extracts the product ID
without any network calls when possible.
"""

import re
from urllib.parse import parse_qs, urlparse

# -- Zepto patterns -------------------------------------------------------
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# Matches /pvid/UUID or /pn/product-slug/UUID
PVID_RE = re.compile(rf"/(?:pvid|pn(?:/[^/]+)?)/({UUID})")
UUID_RE = re.compile(UUID)

# -- Platform host mappings ------------------------------------------------
PLATFORM_HOSTS: dict[str, tuple[str, ...]] = {
    "zepto": ("zepto.com", "zeptonow.com", "zepto.app.link"),
    # instamart.in is Swiggy's dedicated Instamart short domain (share links use it)
    "swiggy": ("swiggy.com", "instamart.in"),
    # BB Now MUST come before bigbasket — bbnow.bigbasket.com would otherwise
    # match bigbasket's endswith(".bigbasket.com") check first.
    "bbnow": ("bbnow.bigbasket.com",),
    "bigbasket": ("bigbasket.com", "bb.com", "bbdaily.com"),
    "blinkit": ("blinkit.com", "grofers.com", "blinkit.app.link"),
    "flipkart": ("flipkart.com",),
}

# -- Per-platform product ID regexes ----------------------------------------
# Swiggy Instamart product URL patterns:
#   swiggy.com:   /instamart/item/{id}  or  /instamart/item/{slug}/{id}
#                 /stores/instamart/item/{id}  or  /stores/instamart/item/{slug}/{id}
#                 /instamart/p/{slug}-{id}
#   instamart.in: /item/{id}?share=true  or  /p/{slug}-{id}
#
# Strategy: the product ID is always the LAST path segment before ? or # or end-of-string.
# Swiggy IDs are alphanumeric (uppercase letters + digits), no dashes/underscores in the ID itself.
# We match the last path component after /item/ or /p/ that is ≥4 chars of [A-Za-z0-9].
SWIGGY_PRODUCT_RE = re.compile(
    r"/(?:stores/)?instamart/(?:item|p)/(?:[^/?#]*/)*(?:[^/?#-]+-)*([A-Za-z0-9]{4,})(?:[/?#]|$)"
)
# instamart.in short-links: https://instamart.in/item/{ID}?share=true
#                           https://instamart.in/p/{slug}-{ID}
INSTAMART_SHORT_RE = re.compile(
    r"instamart\.in/(?:item|p)/(?:[^/?#]*/)*(?:[^/?#-]+-)*([A-Za-z0-9]{6,})(?:[/?#]|$)"
)
# BigBasket product URL: /pd/{product_id}/{slug}/
BB_PRODUCT_RE = re.compile(r"/pd/(\d+)(?:[/?#]|$)")
# Blinkit: /prn/{slug}/prid/{id} OR /pr/{slug}/prid/{id} OR /product/{id}
BLINKIT_PRODUCT_RE = re.compile(r"/prn/[^/]+/prid/(\d+)|/pr(?:n|oduct)?/(?:.*?/prid/)?(\d+)")
# BB Now: same format as BigBasket (/pd/{numeric_id}/)
BBNOW_PRODUCT_RE = re.compile(r"/pd/(\d+)(?:[/?#]|$)")
# Flipkart product ID: /p/{product_id}
FLIPKART_PRODUCT_RE = re.compile(r"/p/([a-zA-Z0-9]+)(?:[/?#]|$)")


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to.

    Returns 'zepto' | 'swiggy' | 'bigbasket' | 'blinkit' | 'flipkart' | 'flipkart_minutes' | None.
    """
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    for platform, hosts in PLATFORM_HOSTS.items():
        if any(host == h or host.endswith("." + h) for h in hosts):
            if platform == "flipkart":
                qs = parse_qs(parsed.query)
                marketplace = qs.get("marketplace", [""])[0].upper()
                if marketplace == "HYPERLOCAL":
                    return "flipkart_minutes"
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
        # Try swiggy.com path pattern first, then instamart.in short-link pattern
        m = SWIGGY_PRODUCT_RE.search(text) or INSTAMART_SHORT_RE.search(text)
        return ("swiggy", m.group(1)) if m else ("swiggy", None)
    elif platform == "bigbasket":
        m = BB_PRODUCT_RE.search(text)
        return ("bigbasket", m.group(1)) if m else ("bigbasket", None)
    elif platform == "blinkit":
        m = BLINKIT_PRODUCT_RE.search(text)
        # The regex has two groups: group(1) for /prn/ pattern, group(2) for legacy /pr/
        pid = (m.group(1) or m.group(2)) if m else None
        return ("blinkit", pid) if pid else ("blinkit", None)
    elif platform == "bbnow":
        m = BBNOW_PRODUCT_RE.search(text)
        return ("bbnow", m.group(1)) if m else ("bbnow", None)
    elif platform == "flipkart" or platform == "flipkart_minutes":
        # Extract pid from query parameters, fallback to regex
        pid = _extract_flipkart_id(text)
        return (platform, pid) if pid else (platform, None)

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


def _extract_flipkart_id(text: str) -> str | None:
    """Pull a Flipkart pid out of a URL or pasted text."""
    try:
        qs = parse_qs(urlparse(text.strip()).query)
        if "pid" in qs and qs["pid"]:
            return qs["pid"][0]
    except ValueError:
        pass
    m = FLIPKART_PRODUCT_RE.search(text)
    if m:
        return m.group(1)
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
