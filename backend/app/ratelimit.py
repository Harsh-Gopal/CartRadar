"""In-memory abuse controls: token-bucket rate limiting and a concurrency gate.

State lives in this process only — fine for a single-instance deployment, which
is what this app is. Run more than one replica and each gets its own buckets.
"""

import time
from collections.abc import Callable


class TokenBucket:
    """Classic token bucket. Starts full; refills continuously up to capacity."""

    def __init__(
        self,
        capacity: float,
        refill_per_sec: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacity = capacity
        self._refill = refill_per_sec
        self._clock = clock
        self._tokens = float(capacity)
        self._updated = clock()

    def _refill_now(self) -> None:
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._refill)
        self._updated = now

    def take(self, cost: float = 1.0) -> bool:
        self._refill_now()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def take_up_to(self, n: int) -> int:
        """Consume and return as many whole tokens as are available, up to n.
        For batch work (e.g. a sweep of n probes) that can proceed partially."""
        if n <= 0:
            return 0
        self._refill_now()
        granted = min(n, int(self._tokens))
        self._tokens -= granted
        return granted

    @property
    def full(self) -> bool:
        return self._tokens >= self._capacity


# Above this many tracked clients, prune buckets that have fully refilled (idle).
# Bounds memory if spoofed client identities flood the maps.
_MAX_CLIENTS = 10_000


class RateLimiter:
    """Per-client request and search budgets, each its own token bucket."""

    def __init__(
        self,
        *,
        request_capacity: float,
        request_refill_per_sec: float,
        search_capacity: float,
        search_refill_per_sec: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._req_cfg = (request_capacity, request_refill_per_sec)
        self._search_cfg = (search_capacity, search_refill_per_sec)
        self._req: dict[str, TokenBucket] = {}
        self._search: dict[str, TokenBucket] = {}

    def allow_request(self, client_id: str) -> bool:
        return self._take(self._req, self._req_cfg, client_id)

    def allow_search(self, client_id: str) -> bool:
        return self._take(self._search, self._search_cfg, client_id)

    def _take(
        self,
        buckets: dict[str, TokenBucket],
        cfg: tuple[float, float],
        client_id: str,
    ) -> bool:
        bucket = buckets.get(client_id)
        if bucket is None:
            if len(buckets) >= _MAX_CLIENTS:
                self._prune(buckets)
            bucket = TokenBucket(cfg[0], cfg[1], self._clock)
            buckets[client_id] = bucket
        return bucket.take()

    @staticmethod
    def _prune(buckets: dict[str, TokenBucket]) -> None:
        for key in [k for k, b in buckets.items() if b.full]:
            del buckets[key]


class ConcurrencyGate:
    """Caps simultaneous in-flight operations. Single-threaded async safe:
    there is no await between the check and the increment."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._active = 0

    def try_acquire(self) -> bool:
        if self._active >= self._limit:
            return False
        self._active += 1
        return True

    def release(self) -> None:
        if self._active > 0:
            self._active -= 1
