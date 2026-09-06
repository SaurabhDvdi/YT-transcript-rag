"""Tests for multi-dimensional rate limiting and concurrent stream tracking."""

import pytest

from src.services.rate_limit.limiter import DistributedRateLimiter


@pytest.mark.asyncio
async def test_distributed_rate_limiter_sliding_window():
    limiter = DistributedRateLimiter()
    key = "test_ip_192.168.1.1"

    # Allow 3 requests in a 10-second window
    assert await limiter.check_rate_limit(key, max_requests=3, window_seconds=10) is True
    assert await limiter.check_rate_limit(key, max_requests=3, window_seconds=10) is True
    assert await limiter.check_rate_limit(key, max_requests=3, window_seconds=10) is True

    # 4th request in the same window is rejected
    assert await limiter.check_rate_limit(key, max_requests=3, window_seconds=10) is False

    # Different key is unaffected
    other_key = "test_ip_10.0.0.1"
    assert await limiter.check_rate_limit(other_key, max_requests=3, window_seconds=10) is True


@pytest.mark.asyncio
async def test_concurrent_stream_tracking():
    limiter = DistributedRateLimiter()
    session_1 = "session_user_alpha"
    session_2 = "session_user_beta"

    # 1. Session 1 acquires stream (limit 1)
    assert await limiter.acquire_stream(session_1, max_concurrent=1) is True

    # 2. Session 1 attempts second concurrent stream -> rejected
    assert await limiter.acquire_stream(session_1, max_concurrent=1) is False

    # 3. Session 2 can concurrently acquire its own stream
    assert await limiter.acquire_stream(session_2, max_concurrent=1) is True

    # 4. Session 1 releases its stream
    await limiter.release_stream(session_1)

    # 5. Session 1 can now acquire a stream again
    assert await limiter.acquire_stream(session_1, max_concurrent=1) is True

    # Clean up
    await limiter.release_stream(session_1)
    await limiter.release_stream(session_2)
