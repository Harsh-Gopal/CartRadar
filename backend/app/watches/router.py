"""
Worth-It watches API router.

Endpoints:
  POST   /api/watches                — create a new watch
  GET    /api/watches                — list all watches
  GET    /api/watches/{id}           — get watch + recent events
  PATCH  /api/watches/{id}           — update watch (pause/resume/edit)
  DELETE /api/watches/{id}           — delete watch
  POST   /api/watches/{id}/scan-now  — trigger immediate scan
  GET    /api/watches/{id}/console   — SSE live console stream
  POST   /api/telegram/configure     — save Telegram bot token + chat_id
  GET    /api/telegram/status        — check Telegram config
  POST   /api/telegram/test          — send test message
  POST   /api/watches/resolve-url    — resolve URL to product info
"""

from __future__ import annotations

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from .models import Watch, VALID_INTERVALS
from .db import WatchDB
from .console import get_console, remove_console
from .telegram import verify_bot_token, send_message
from .settings import get_telegram_bot_token, get_telegram_chat_id, set_telegram_config, clear_telegram_config
from . import scheduler as sched

log = logging.getLogger("watches.router")

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# ── Dependency: WatchDB ───────────────────────────────────────────────────────

def get_db(request: Request) -> WatchDB:
    return request.app.state.watch_db


# ── Request / Response models ─────────────────────────────────────────────────

class CreateWatchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    product_url: str = Field(min_length=5)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=10.0, ge=1.0, le=30.0)
    interval_minutes: int = Field(default=15)
    in_stock_only: bool = True
    max_price: Optional[float] = None
    min_discount_pct: Optional[float] = None
    telegram_chat_id: Optional[str] = None
    notify_browser: bool = True

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v not in VALID_INTERVALS:
            raise ValueError(f"interval_minutes must be one of {VALID_INTERVALS}")
        return v


class UpdateWatchRequest(BaseModel):
    status: Optional[str] = None        # active | paused
    name: Optional[str] = None
    interval_minutes: Optional[int] = None
    max_price: Optional[float] = None
    min_discount_pct: Optional[float] = None
    in_stock_only: Optional[bool] = None
    radius_km: Optional[float] = None
    telegram_chat_id: Optional[str] = None
    notify_browser: Optional[bool] = None

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in VALID_INTERVALS:
            raise ValueError(f"interval_minutes must be one of {VALID_INTERVALS}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "paused"):
            raise ValueError("status must be 'active' or 'paused'")
        return v


class ResolveUrlRequest(BaseModel):
    url: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class TelegramConfigRequest(BaseModel):
    bot_token: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)


class TelegramTestRequest(BaseModel):
    chat_id: Optional[str] = None  # override global if provided


# ── Helpers ───────────────────────────────────────────────────────────────────

def _watch_to_dict(watch: Watch) -> dict:
    d = asdict(watch)
    # Convert datetimes to ISO strings for JSON
    for key in ("created_at", "last_scan_at", "next_scan_at"):
        val = d.get(key)
        if hasattr(val, "isoformat"):
            d[key] = val.isoformat()
        # already a string or None — leave as-is
    return d


def _event_to_dict(event) -> dict:
    d = asdict(event)
    val = d.get("scanned_at")
    if hasattr(val, "isoformat"):
        d["scanned_at"] = val.isoformat()
    return d


# ── Watch endpoints ───────────────────────────────────────────────────────────

@router.post("/watches")
async def create_watch(body: CreateWatchRequest, request: Request):
    """Create a new watch. Resolves the product URL and schedules scanning."""
    db: WatchDB = get_db(request)
    clients: dict = request.app.state.clients

    # Resolve product URL
    from ..links import extract_product_id, first_url
    url = body.product_url.strip()
    # Handle pasted share text with embedded URL
    extracted_url = first_url(url) or url
    platform, product_id = extract_product_id(extracted_url)

    if not platform:
        raise HTTPException(status_code=422, detail="URL not recognised. Paste a product link from Zepto, Instamart, BigBasket, or Blinkit.")
    if not product_id:
        raise HTTPException(status_code=422, detail=f"Could not extract product ID from the {platform} URL. Make sure you paste the full product link.")
    if platform not in clients:
        raise HTTPException(status_code=422, detail=f"Platform '{platform}' is not currently enabled.")

    # Quick product resolve to get name + image (best-effort, don't fail watch creation)
    product_name: Optional[str] = None
    product_image: Optional[str] = None

    client = clients[platform]
    if body.lat and body.lng:
        try:
            resolution = await asyncio.wait_for(
                client.resolve_store(body.lat, body.lng, product_id=product_id),
                timeout=10.0
            )
            if resolution and resolution.serviceable:
                result = await asyncio.wait_for(
                    client.product_at_store(product_id, resolution.store_id, lat=body.lat, lng=body.lng),
                    timeout=10.0
                )
                if result:
                    product_name = result.name
                    product_image = result.image_url
        except Exception as e:
            log.warning("Could not resolve product name for %s/%s: %s", platform, product_id, e)

    watch = Watch(
        id=str(uuid.uuid4()),
        name=body.name,
        platform=platform,
        product_id=product_id,
        product_url=extracted_url,
        product_name=product_name,
        product_image=product_image,
        lat=body.lat,
        lng=body.lng,
        radius_km=body.radius_km,
        in_stock_only=body.in_stock_only,
        max_price=body.max_price,
        min_discount_pct=body.min_discount_pct,
        interval_minutes=body.interval_minutes,
        telegram_chat_id=body.telegram_chat_id,
        notify_browser=body.notify_browser,
        created_at=datetime.now(timezone.utc),
    )

    db.create_watch(watch)
    sched.schedule_new_watch(watch)

    log.info("Watch created: %s (%s/%s) every %dmin", watch.id, platform, product_id, body.interval_minutes)
    return _watch_to_dict(watch)


@router.get("/watches")
async def list_watches(request: Request):
    db: WatchDB = get_db(request)
    watches = db.list_watches()
    return {"watches": [_watch_to_dict(w) for w in watches]}


@router.get("/watches/{watch_id}")
async def get_watch(watch_id: str, request: Request):
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    events = db.list_events(watch_id, limit=20)
    return {
        "watch": _watch_to_dict(watch),
        "events": [_event_to_dict(e) for e in events],
    }


@router.patch("/watches/{watch_id}")
async def update_watch(watch_id: str, body: UpdateWatchRequest, request: Request):
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    if body.status is not None:
        db.update_watch_status(watch_id, body.status)

    db.update_watch(
        watch_id,
        name=body.name,
        interval_minutes=body.interval_minutes,
        max_price=body.max_price,
        min_discount_pct=body.min_discount_pct,
        in_stock_only=body.in_stock_only,
        radius_km=body.radius_km,
        telegram_chat_id=body.telegram_chat_id,
        notify_browser=body.notify_browser,
    )

    watch = db.get_watch(watch_id)
    sched.reschedule_watch(watch)

    return _watch_to_dict(watch)


@router.delete("/watches/{watch_id}")
async def delete_watch(watch_id: str, request: Request):
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    sched.unschedule_watch(watch_id)
    db.delete_watch(watch_id)
    remove_console(watch_id)
    return {"status": "deleted", "id": watch_id}


@router.post("/watches/{watch_id}/scan-now")
async def scan_now(watch_id: str, request: Request):
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    event = await sched.trigger_scan_now(watch_id)
    return {"status": "ok", "event": _event_to_dict(event) if event else None}


@router.get("/watches/{watch_id}/console")
async def watch_console_sse(watch_id: str, request: Request):
    """SSE endpoint — streams real-time log events for a watch's scan lifecycle."""
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    console = get_console(watch_id)

    async def stream():
        async for chunk in console.stream():
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/watches/{watch_id}/events")
async def get_watch_events(watch_id: str, request: Request, limit: int = 50):
    db: WatchDB = get_db(request)
    watch = db.get_watch(watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    events = db.list_events(watch_id, limit=limit)
    return {"events": [_event_to_dict(e) for e in events]}


# ── Telegram endpoints ────────────────────────────────────────────────────────

@router.post("/telegram/configure")
async def configure_telegram(body: TelegramConfigRequest):
    """Verify and save Telegram bot token + chat_id."""
    try:
        bot_info = await verify_bot_token(body.bot_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    set_telegram_config(body.bot_token, body.chat_id)
    return {
        "status": "ok",
        "bot_username": bot_info.get("username"),
        "bot_name": bot_info.get("first_name"),
    }


@router.get("/telegram/status")
async def telegram_status():
    token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()
    return {
        "configured": bool(token),
        "has_chat_id": bool(chat_id),
        "chat_id": chat_id,
    }


@router.delete("/telegram/configure")
async def remove_telegram():
    clear_telegram_config()
    return {"status": "ok"}


@router.post("/telegram/test")
async def test_telegram(body: TelegramTestRequest):
    token = get_telegram_bot_token()
    if not token:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")

    chat_id = body.chat_id or get_telegram_chat_id()
    if not chat_id:
        raise HTTPException(status_code=400, detail="No Telegram chat_id configured")

    ok = await send_message(
        chat_id,
        "🔔 *Worth-It Test Message*\n\nYour Telegram integration is working correctly. You'll receive deal alerts here.",
        token=token,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to send test message. Check your bot token and chat_id.")

    return {"status": "ok", "message": "Test message sent successfully"}


# ── URL resolution endpoint ───────────────────────────────────────────────────

@router.post("/watches/resolve-url")
async def resolve_url(body: ResolveUrlRequest, request: Request):
    """
    Parse a product URL and return the extracted platform + product_id + metadata.
    Used by the frontend to preview product info before creating a watch.
    """
    from ..links import extract_product_id, first_url

    url = body.url.strip()
    extracted_url = first_url(url) or url
    platform, product_id = extract_product_id(extracted_url)

    if not platform:
        raise HTTPException(status_code=422, detail="URL not recognised. Paste a product link from Zepto, Instamart, BigBasket, or Blinkit.")
    if not product_id:
        raise HTTPException(status_code=422, detail=f"Could not extract product ID from this {platform} URL.")

    result = {
        "platform": platform,
        "product_id": product_id,
        "product_url": extracted_url,
        "product_name": None,
        "product_image": None,
    }

    # Try to fetch product name + image if lat/lng provided
    clients = request.app.state.clients
    client = clients.get(platform)
    if client and body.lat and body.lng:
        try:
            resolution = await asyncio.wait_for(
                client.resolve_store(body.lat, body.lng, product_id=product_id),
                timeout=10.0,
            )
            if resolution and resolution.serviceable and resolution.store_id:
                product_result = await asyncio.wait_for(
                    client.product_at_store(product_id, resolution.store_id, lat=body.lat, lng=body.lng),
                    timeout=10.0,
                )
                if product_result:
                    result["product_name"] = product_result.name
                    result["product_image"] = getattr(product_result, "image_url", None)
        except Exception as e:
            log.warning("Could not fetch product metadata: %s", e)

    return result
