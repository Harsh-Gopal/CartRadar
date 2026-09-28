"""Per-watch SSE log ring buffer for the live console.

Each watch has an in-memory ring buffer of the last MAX_BUFFER_EVENTS log entries.
The SSE endpoint streams the buffered history + live events to connected clients.

Design:
- Pure in-memory — no database writes for console events (they're ephemeral UI data)
- asyncio.Queue per watch for live events
- Ring buffer (collections.deque) for history replay on new connections
- Keepalive ping every 15 seconds so proxies don't close idle SSE connections
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any, AsyncGenerator, Dict, Deque

MAX_BUFFER_EVENTS = 200   # per-watch ring buffer size
KEEPALIVE_SECONDS = 15    # send :ping every N seconds


class WatchConsole:
    """Thread-safe ring buffer + asyncio queue for a single watch's console log."""

    def __init__(self, watch_id: str):
        self.watch_id = watch_id
        self._buffer: Deque[dict] = deque(maxlen=MAX_BUFFER_EVENTS)
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    def emit(self, level: str, message: str, extra: dict | None = None) -> None:
        """
        Emit a log event.  Safe to call from sync or async code.
        level: 'info' | 'warn' | 'error' | 'success' | 'debug'
        """
        event = {
            "ts": time.time(),
            "level": level,
            "msg": message,
        }
        if extra:
            event.update(extra)
        self._buffer.append(event)
        # Non-blocking push to all subscriber queues
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow consumer — skip this event for that client

    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted strings.
        Replays buffer history first, then streams live events.
        """
        # Replay history
        history = list(self._buffer)
        for event in history:
            yield f"data: {json.dumps(event)}\n\n"

        # Subscribe to live events
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping — SSE comment line, keeps connection alive through proxies
                    yield ": ping\n\n"
        finally:
            async with self._lock:
                try:
                    self._subscribers.remove(queue)
                except ValueError:
                    pass


# ── Global registry ───────────────────────────────────────────────────────────

_consoles: Dict[str, WatchConsole] = {}
_registry_lock = asyncio.Lock()


def get_console(watch_id: str) -> WatchConsole:
    """Get or create the console for a watch."""
    if watch_id not in _consoles:
        _consoles[watch_id] = WatchConsole(watch_id)
    return _consoles[watch_id]


def remove_console(watch_id: str) -> None:
    """Remove console when a watch is deleted."""
    _consoles.pop(watch_id, None)


def emit_log(watch_id: str, level: str, message: str, **extra) -> None:
    """Shortcut to emit a log event to a watch's console."""
    get_console(watch_id).emit(level, message, extra or None)
