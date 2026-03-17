"""Tests for rate limit tracking and throttling."""

import pytest

from autotask.rate_limiter import RateLimiter


async def test_rate_limiter_no_delay_when_fresh() -> None:
    """No delay when rate limiter has no data."""
    rl = RateLimiter()
    delay = rl.get_delay()
    assert delay == 0.0


async def test_rate_limiter_delay_at_50_percent() -> None:
    """0.5s delay when usage hits 50%."""
    rl = RateLimiter()
    rl.update(current_count=5000, threshold=10000)
    delay = rl.get_delay()
    assert delay == pytest.approx(0.5)


async def test_rate_limiter_delay_at_75_percent() -> None:
    """1.0s delay when usage hits 75%."""
    rl = RateLimiter()
    rl.update(current_count=7500, threshold=10000)
    delay = rl.get_delay()
    assert delay == pytest.approx(1.0)


async def test_rate_limiter_no_delay_below_50_percent() -> None:
    """No delay when usage is below 50%."""
    rl = RateLimiter()
    rl.update(current_count=4000, threshold=10000)
    delay = rl.get_delay()
    assert delay == 0.0
