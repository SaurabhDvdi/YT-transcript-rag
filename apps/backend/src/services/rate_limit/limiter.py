"""Multi-dimensional rate limiting and concurrent stream tracking."""

import time
from typing import Any, Protocol


class RateLimiter(Protocol):
    """Protocol for distributed rate limiting and active stream concurrency control."""

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool: ...

    async def acquire_stream(self, session_id: str, max_concurrent: int = 1) -> bool: ...

    async def release_stream(self, session_id: str) -> None: ...


class DistributedRateLimiter:
    """Rate limiter supporting Cloudflare ratelimit binding with in-memory sliding window fallback."""

    def __init__(self, cf_rate_limiter: Any | None = None) -> None:
        self.cf_limiter = cf_rate_limiter
        # key -> [timestamps_in_epoch_seconds]
        self._buckets: dict[str, list[float]] = {}
        # session_id -> active_stream_count
        self._active_streams: dict[str, int] = {}

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        # 1. Use Cloudflare Rate Limiter binding if configured in production
        if self.cf_limiter is not None and hasattr(self.cf_limiter, "limit"):
            try:
                res = await self.cf_limiter.limit({"key": key})
                if isinstance(res, dict) and "success" in res:
                    return bool(res["success"])
                if hasattr(res, "success"):
                    return bool(res.success)
            except Exception:
                pass  # Fall back to sliding window

        # 2. Sliding-window in-memory fallback
        now = time.time()
        window_start = now - window_seconds

        timestamps = self._buckets.get(key, [])
        # Evict timestamps older than the window
        valid_timestamps = [t for t in timestamps if t > window_start]

        if len(valid_timestamps) >= max_requests:
            self._buckets[key] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self._buckets[key] = valid_timestamps
        return True

    async def acquire_stream(self, session_id: str, max_concurrent: int = 1) -> bool:
        current = self._active_streams.get(session_id, 0)
        if current >= max_concurrent:
            return False
        self._active_streams[session_id] = current + 1
        return True

    async def release_stream(self, session_id: str) -> None:
        current = self._active_streams.get(session_id, 0)
        if current <= 1:
            self._active_streams.pop(session_id, None)
        else:
            self._active_streams[session_id] = current - 1

    def reset(self) -> None:
        self._buckets.clear()
        self._active_streams.clear()
