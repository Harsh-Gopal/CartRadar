"""Telegram notification helpers for Worth-It watch alerts."""

from __future__ import annotations

import asyncio
import logging
import httpx
from typing import Optional

from .models import Watch, WatchEvent
from .settings import get_telegram_bot_token

log = logging.getLogger("watches.telegram")


async def verify_bot_token(token: str) -> dict:
    """
    Verify a Telegram bot token by calling getMe.
    Returns bot info dict or raises ValueError on invalid token.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        if resp.status_code != 200:
            raise ValueError(f"Telegram returned HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if not data.get("ok"):
            raise ValueError(f"Telegram API error: {data.get('description', 'unknown')}")
        return data.get("result", {})


async def send_message(chat_id: str, text: str, token: Optional[str] = None) -> bool:
    """
    Send a Telegram message to a chat ID.
    Returns True on success, False on failure.
    """
    token = token or get_telegram_bot_token()
    if not token:
        log.warning("No Telegram bot token configured — skipping notification")
        return False

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            if resp.status_code == 200:
                return True
            log.error("Telegram sendMessage failed: HTTP %s — %s", resp.status_code, resp.text[:200])
            return False
        except Exception as e:
            log.error("Telegram sendMessage exception: %s", e)
            return False


def format_alert_message(watch: Watch, event: WatchEvent) -> str:
    """Format a Telegram alert message for a qualifying deal event."""
    lines = [
        f"🔔 *Worth-It Alert: {watch.name}*",
        "",
    ]

    if event.price is not None:
        price_line = f"💰 ₹{event.price:.0f}"
        if event.mrp and event.mrp > event.price:
            price_line += f"  ~~₹{event.mrp:.0f}~~"
        if event.discount_pct:
            price_line += f"  *{event.discount_pct:.0f}% OFF*"
        lines.append(price_line)

    if event.store_name:
        store_line = f"📍 {event.store_name}"
        if event.distance_km is not None:
            store_line += f" ({event.distance_km:.1f} km)"
        lines.append(store_line)

    if event.notes:
        lines.append(f"_ℹ️ {event.notes}_")

    lines.append("")
    lines.append(f"[🛒 View on {watch.platform.title()}]({watch.product_url})")

    return "\n".join(lines)


async def send_watch_alert(watch: Watch, event: WatchEvent, chat_id: Optional[str] = None) -> bool:
    """Send a formatted deal alert for a watch event."""
    target_chat = chat_id or watch.telegram_chat_id
    if not target_chat:
        log.debug("Watch %s has no telegram_chat_id — skipping alert", watch.id)
        return False

    text = format_alert_message(watch, event)
    return await send_message(target_chat, text)
