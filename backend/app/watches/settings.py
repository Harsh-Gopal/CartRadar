"""User settings persistence (Telegram bot token, chat ID, etc.)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("watches.settings")

_SETTINGS_FILE = Path(os.environ.get("WATCH_SETTINGS_PATH", "data/watch_settings.json"))


def _load() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text())
    except Exception as e:
        log.error("Failed to read watch_settings.json: %s", e)
    return {}


def _save(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def get_telegram_bot_token() -> Optional[str]:
    return _load().get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")


def get_telegram_chat_id() -> Optional[str]:
    return _load().get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID")


def set_telegram_config(bot_token: str, chat_id: str) -> None:
    data = _load()
    data["telegram_bot_token"] = bot_token
    data["telegram_chat_id"] = chat_id
    _save(data)


def clear_telegram_config() -> None:
    data = _load()
    data.pop("telegram_bot_token", None)
    data.pop("telegram_chat_id", None)
    _save(data)
