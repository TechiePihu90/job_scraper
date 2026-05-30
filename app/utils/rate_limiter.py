"""Async token-bucket rate limiter per domain."""

from __future__ import annotations

import asyncio
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Token-bucket rate limiter keyed by domain.

    Usage:
        limiter = AsyncRateLimiter(rate=5.0)   # 5 requests/sec
        async with limiter("example.com"):
            await session.get(url)
    """

    def __init__(self, rate: float = 5.0) -> None:
        """
        Args:
            rate: Maximum requests per second per domain.
        """
        self._rate = rate
        self._interval = 1.0 / rate
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_call: dict[str, float] = defaultdict(float)

    def __call__(self, domain: str) -> "_RateLimitContext":
        return _RateLimitContext(self, domain)

    async def acquire(self, domain: str) -> None:
        """Wait until a request slot is available for the given domain."""
        async with self._locks[domain]:
            now = time.monotonic()
            elapsed = now - self._last_call[domain]
            if elapsed < self._interval:
                wait = self._interval - elapsed
                logger.debug("Rate limiting %s: waiting %.3fs", domain, wait)
                await asyncio.sleep(wait)
            self._last_call[domain] = time.monotonic()


class _RateLimitContext:
    """Async context manager for the rate limiter."""

    def __init__(self, limiter: AsyncRateLimiter, domain: str) -> None:
        self._limiter = limiter
        self._domain = domain

    async def __aenter__(self) -> None:
        await self._limiter.acquire(self._domain)

    async def __aexit__(self, *exc: object) -> None:
        pass
