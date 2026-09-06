import asyncio
import contextlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class CacheService(Protocol):
    """Protocol for caching with TTL and key-prefix invalidation."""

    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...

    async def get_or_compute(
        self, key: str, compute_func: Callable[[], Awaitable[T]], ttl_seconds: int = 3600
    ) -> T: ...


class InMemoryCacheService:
    """In-memory cache with TTL expiration and single-flight stampede protection."""

    def __init__(self) -> None:
        # key -> (value, expire_timestamp_epoch)
        self._store: dict[str, tuple[Any, float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        val, expire_at = entry
        if time.time() > expire_at:
            self._store.pop(key, None)
            return None
        return val

    async def set(self, key: str, value: Any, ttl_seconds: float = 3600.0) -> None:
        expire_at = time.time() + float(ttl_seconds)
        self._store[key] = (value, expire_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._locks.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        keys_to_del = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_del:
            self._store.pop(k, None)
            self._locks.pop(k, None)

    async def clear_prefix(self, prefix: str) -> None:
        await self.delete_prefix(prefix)

    def clear(self) -> None:
        self._store.clear()
        self._locks.clear()

    async def get_or_compute(
        self, key: str, compute_func: Callable[[], Awaitable[T]], ttl_seconds: int = 3600
    ) -> T:
        # Fast path: check cache before lock
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        # Stampede lock: ensure only one compute occurs for this key
        lock = self._get_lock(key)
        async with lock:
            # Double-check after acquiring lock
            cached = await self.get(key)
            if cached is not None:
                return cached  # type: ignore[no-any-return]

            computed = await compute_func()
            await self.set(key, computed, ttl_seconds)
            return computed


class KVCacheService:
    """Cloudflare Workers KV-backed cache with in-memory stampede mitigation."""

    def __init__(self, kv_binding: Any, local_fallback: InMemoryCacheService | None = None) -> None:
        self.kv = kv_binding
        self.local = local_fallback or InMemoryCacheService()

    async def get(self, key: str) -> Any | None:
        # Check local short-term memory first
        local_val = await self.local.get(key)
        if local_val is not None:
            return local_val

        if not hasattr(self.kv, "get") or not callable(self.kv.get):
            return None

        try:
            raw = await self.kv.get(key)
            if not raw:
                return None
            val = json.loads(raw)
            # Store in short-term local cache to save KV reads
            await self.local.set(key, val, ttl_seconds=30)
            return val
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        await self.local.set(key, value, ttl_seconds)
        if hasattr(self.kv, "put") and callable(self.kv.put):
            with contextlib.suppress(Exception):
                raw = json.dumps(value)
                await self.kv.put(key, raw, expirationTtl=max(60, ttl_seconds))

    async def delete(self, key: str) -> None:
        await self.local.delete(key)
        if hasattr(self.kv, "delete") and callable(self.kv.delete):
            with contextlib.suppress(Exception):
                await self.kv.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        await self.local.delete_prefix(prefix)
        # Note: KV list on free tier is limited to 1,000 ops/day.
        # Local prefix invalidation suffices for immediate consistency.

    async def get_or_compute(
        self, key: str, compute_func: Callable[[], Awaitable[T]], ttl_seconds: int = 3600
    ) -> T:
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        return await self.local.get_or_compute(
            key,
            lambda: self._compute_and_save(key, compute_func, ttl_seconds),
            ttl_seconds,
        )

    async def _compute_and_save(
        self, key: str, compute_func: Callable[[], Awaitable[T]], ttl_seconds: int
    ) -> T:
        res = await compute_func()
        await self.set(key, res, ttl_seconds)
        return res
