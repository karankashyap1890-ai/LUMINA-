"""
Lumina Security — Sliding-Window Rate Limiter
In-memory per-IP rate limiting with FastAPI dependency injection.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter.

    Keeps a deque of request timestamps per client identifier.
    Expired entries are pruned on each check, so memory is bounded
    by `max_requests * active_clients`.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: Dict[str, Deque[float]] = defaultdict(deque)

    # ── Public API ───────────────────────────────────────────────────────────

    def is_allowed(self, identifier: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        bucket = self._store[identifier]

        # Evict stale entries
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) < self.max_requests:
            bucket.append(now)
            return True
        return False

    def remaining(self, identifier: str) -> int:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        bucket = self._store[identifier]
        in_window = sum(1 for ts in bucket if ts >= cutoff)
        return max(0, self.max_requests - in_window)

    def reset(self, identifier: str) -> None:
        self._store.pop(identifier, None)


# ── Singleton instance ───────────────────────────────────────────────────────
_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency: enforces rate limit, raises HTTP 429 on breach."""
    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.is_allowed(client_ip):
        left = _limiter.remaining(client_ip)
        logger.warning(f"Rate-limit breach from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — please wait 60 s before retrying.",
            headers={
                "X-RateLimit-Limit": str(_limiter.max_requests),
                "X-RateLimit-Remaining": str(left),
                "Retry-After": "60",
            },
        )
