"""Rate limit tracking for Autotask API.

Autotask enforces 10k requests/hour shared across ALL integrations
on the account. Progressive throttling:
- 50% usage (5000 req) = 0.5s delay between requests
- 75% usage (7500 req) = 1.0s delay between requests
"""

from __future__ import annotations

import asyncio


class RateLimiter:
    """Tracks API rate limit usage and applies progressive delays."""

    def __init__(self) -> None:
        self._current_count: int = 0
        self._threshold: int = 10000

    def update(self, current_count: int, threshold: int) -> None:
        """Update rate limit state from API response headers."""
        self._current_count = current_count
        self._threshold = threshold

    def get_delay(self) -> float:
        """Calculate delay based on current usage percentage."""
        if self._threshold == 0:
            return 0.0

        usage_pct = self._current_count / self._threshold

        if usage_pct >= 0.75:
            return 1.0
        elif usage_pct >= 0.50:
            return 0.5
        return 0.0

    async def wait_if_needed(self) -> None:
        """Sleep if rate limiting requires a delay."""
        delay = self.get_delay()
        if delay > 0:
            await asyncio.sleep(delay)
