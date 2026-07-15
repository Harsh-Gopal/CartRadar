"""Cart Radar — unified FastAPI app for multi-platform stock checking.

Routes auto-detect which platform a link belongs to and dispatch to the
correct PlatformClient.
"""

import hmac
import json
import logging
from ipaddress import ip_address
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .links import detect_platform, extract_product_id, first_url, looks_like_product_link
from .platforms.base import PlatformClient, PlatformError
from .platforms.zepto import SAMPLE_STORE_ID, ZeptoClient
from .platforms.swiggy import SwiggyClient
from .platforms.bigbasket import BigBasketClient
from .platforms.blinkit import BlinkitClient
from .ratelimit import ConcurrencyGate, RateLimiter, TokenBucket
from .search import run_search
from .store_cache import StoreCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("main")


def _create_clients() -> dict[str, PlatformClient]:
    """Instantiate enabled platform clients."""
    clients: dict[str, PlatformClient] = {}
    if "zepto" in config.ENABLED_PLATFORMS:
        clients["zepto"] = ZeptoClient(config.PROXY_URL, config.ZEPTO_CONCURRENCY)
    if "swiggy" in config.ENABLED_PLATFORMS:
        clients["swiggy"] = SwiggyClient(config.PROXY_URL, config.SWIGGY_CONCURRENCY)
    if "bigbasket" in config.ENABLED_PLATFORMS:
        clients["bigbasket"] = BigBasketClient(config.PROXY_URL, config.BB_CONCURRENCY)
    if "blinkit" in config.ENABLED_PLATFORMS:
        clients["blinkit"] = BlinkitClient(config.PROXY_URL, 5) # Default 5 concurrency
    log.info("enabled platforms: %s", list(clients.keys()))
    return clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clients = _create_clients()
    app.state.cache = StoreCache(config.DATABASE_PATH)
    app.state.limiter = RateLimiter(
        request_capacity=config.REQUEST_BURST,
        request_refill_per_sec=config.REQUESTS_PER_MIN / 60,
        search_capacity=config.SEARCH_BURST,
        search_refill_per_sec=config.SEARCHES_PER_DAY / 86_400,
    )
    app.state.search_gate = ConcurrencyGate(config.MAX_CONCURRENT_SEARCHES)
    app.state.global_searches = TokenBucket(
        config.GLOBAL_SEARCH_BURST, config.GLOBAL_SEARCHES_PER_DAY / 86_400
    )
    app.state.probe_budget = TokenBucket(
        config.PROBE_BURST, config.PROBES_PER_DAY / 86_400
    )
    yield
    for client in app.state.clients.values():
        await client.aclose()
    # Close shared Playwright browser (Blinkit)
    try:
        from .platforms.blinkit import _close_browser as blinkit_close
        await blinkit_close()
    except Exception:
        pass
    app.state.cache.close()



app = FastAPI(title="cart-radar", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- helpers ----------------------------------------------------------------

def get_client(platform: str, request: Request) -> PlatformClient:
    """Get the client for a platform, or raise 422."""
    client = request.app.state.clients.get(platform)
    if not client:
        raise HTTPException(422, f"Platform '{platform}' is not enabled on this instance.")
    return client


# -- abuse controls ---------------------------------------------------------

def client_ip(request: Request) -> str:
    if config.TRUST_FORWARDED_FOR:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1", "0:0:0:0:0:0:0:1"}:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _local_requests_are_unmetered(request: Request) -> bool:
    return _is_loopback_host(request.url.hostname) or _is_loopback_host(client_ip(request))


def _provided_token(request: Request) -> str | None:
    return request.headers.get("x-app-token") or request.query_params.get("token")


def auth_ok(request: Request) -> bool:
    if not config.APP_TOKEN:
        return True
    token = _provided_token(request)
    return bool(token) and hmac.compare_digest(token, config.APP_TOKEN)


async def require_rate(request: Request) -> None:
    if config.DEV_MODE or _local_requests_are_unmetered(request):
        return
    if not request.app.state.limiter.allow_request(client_ip(request)):
        raise HTTPException(429, "Too many requests. Slow down for a bit.")


async def require_access(request: Request) -> None:
    if not auth_ok(request):
        raise HTTPException(401, "Access token missing or invalid.")
    await require_rate(request)


# -- routes -----------------------------------------------------------------

class ResolveRequest(BaseModel):
    url: str
    lat: float | None = None
    lng: float | None = None


@app.get("/api/config")
async def public_config(_: None = Depends(require_rate)):
    """Settings the frontend needs before it can talk to the gated endpoints."""
    return {
        "auth_required": config.APP_TOKEN is not None,
        "max_radius_km": config.MAX_RADIUS_KM,
        "enabled_platforms": config.ENABLED_PLATFORMS,
    }


@app.post("/api/resolve", dependencies=[Depends(require_access)])
async def resolve_link(body: ResolveRequest, request: Request):
    """Share link (any platform) → product info + detected platform.

    Auto-detects which platform the URL belongs to.
    """
    text = body.url.strip()
    platform_name, product_id = extract_product_id(text)

    if not platform_name:
        url = first_url(text)
        if url:
            platform_name = detect_platform(url)

    if not platform_name:
        raise HTTPException(422, "That doesn't look like a recognised product link. Supported: Zepto, Swiggy Instamart, BigBasket.")

    client = get_client(platform_name, request)

    if not product_id:
        url = first_url(text) or text
        product_id = await client.resolve_share_link(url)

    if not product_id:
        raise HTTPException(422, f"Couldn't find a product ID in that {client.display_name} link.")

    # Fetch a product card for display
    try:
        if platform_name == "zepto":
            # Zepto needs a store context to fetch product details
            store_id = SAMPLE_STORE_ID
            if body.lat is not None and body.lng is not None:
                try:
                    home = await client.resolve_store(body.lat, body.lng)
                    if home.serviceable and home.store_id:
                        store_id = home.store_id
                except PlatformError:
                    pass
            product = await client.product_at_store(product_id, store_id)
        else:
            # Other platforms: try product_at_location if coords are available
            if body.lat is not None and body.lng is not None:
                product = await client.product_at_location(product_id, body.lat, body.lng)
            else:
                # No coords — fetch metadata using fallback location (Bangalore)
                try:
                    product = await client.product_at_store(product_id, "dummy", 12.9716, 77.5946)
                except Exception as e:
                    log.warning("Fallback metadata fetch failed: %s", e)
                    product = None
    except PlatformError as e:
        raise HTTPException(502, f"{client.display_name} API error: {e}")

    return {
        "pvid": product_id,
        "platform": platform_name,
        "display_name": client.display_name,
        "product": asdict(product) if product else None,
    }


@app.get("/api/geocode", dependencies=[Depends(require_access)])
async def geocode(q: str = Query(min_length=2), request: Request = None):
    """Geocode using the first available platform geocoder (Zepto's)."""
    # Use Zepto's geocoder as the default since it's backed by Google Maps
    zepto = request.app.state.clients.get("zepto")
    if zepto and zepto.supports_geocoding:
        try:
            result = await zepto.geocode(q)
        except PlatformError as e:
            raise HTTPException(502, f"Geocoding error: {e}")
        if not result:
            raise HTTPException(404, "Location not found. Try a pincode or locality name.")
        return result
    raise HTTPException(501, "No geocoding provider available. Enable Zepto platform.")


@app.get("/api/suggest", dependencies=[Depends(require_access)])
async def suggest(q: str = Query(min_length=2), request: Request = None):
    """Place autocomplete using Zepto's geocoder."""
    zepto = request.app.state.clients.get("zepto")
    if zepto and zepto.supports_geocoding:
        try:
            return {"suggestions": await zepto.autocomplete(q)}
        except PlatformError as e:
            raise HTTPException(502, f"Geocoding error: {e}")
    raise HTTPException(501, "No geocoding provider available.")


@app.get("/api/place", dependencies=[Depends(require_access)])
async def place(place_id: str = Query(min_length=4), label: str = "", request: Request = None):
    zepto = request.app.state.clients.get("zepto")
    if zepto and hasattr(zepto, "place_details"):
        try:
            result = await zepto.place_details(place_id, label)
        except PlatformError as e:
            raise HTTPException(502, f"Geocoding error: {e}")
        if not result:
            raise HTTPException(404, "Couldn't locate that place.")
        return result
    raise HTTPException(501, "No geocoding provider available.")


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _sse_error(message: str) -> StreamingResponse:
    async def stream():
        yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/api/search")
async def search(
    request: Request,
    pvid: str = Query(min_length=1),
    platform: str = Query(default="zepto"),
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=10, ge=1, le=config.MAX_RADIUS_KM),
    force: bool = Query(default=False),
):
    """SSE stream: search for product availability across stores.

    The `platform` param selects which platform to search on.
    """
    state = request.app.state
    if not auth_ok(request):
        return _sse_error("Access token missing or invalid.")

    client = state.clients.get(platform)
    if not client:
        return _sse_error(f"Platform '{platform}' is not enabled.")

    metered = not (config.DEV_MODE or _local_requests_are_unmetered(request))
    acquired_gate = False

    if metered:
        if not state.search_gate.try_acquire():
            return _sse_error("The server is busy — try again shortly.")
        acquired_gate = True
        if not state.limiter.allow_search(client_ip(request)):
            state.search_gate.release()
            return _sse_error("You've reached your search limit. Try again later.")
        if not state.global_searches.take():
            state.search_gate.release()
            return _sse_error("Today's search limit reached. Try again later.")

    async def stream():
        try:
            async for event in run_search(
                client, state.cache, pvid, lat, lng, radius_km, force,
                probe_budget=None if (config.DEV_MODE or _local_requests_are_unmetered(request)) else state.probe_budget,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if acquired_gate:
                state.search_gate.release()

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/api/platforms", dependencies=[Depends(require_access)])
async def list_platforms(request: Request):
    """List all enabled platforms and their capabilities."""
    return {
        "platforms": [
            {
                "name": client.platform_name,
                "display_name": client.display_name,
                "supports_sweep": client.supports_sweep,
                "supports_geocoding": client.supports_geocoding,
            }
            for client in request.app.state.clients.values()
        ]
    }


@app.get("/api/stats", dependencies=[Depends(require_access)])
async def stats(request: Request):
    return request.app.state.cache.stats()


if config.STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")
