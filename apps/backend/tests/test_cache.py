"""Tests for caching layer and stampede protection."""

import asyncio
from typing import Any

import pytest

from src.services.cache.service import InMemoryCacheService, KVCacheService


@pytest.mark.asyncio
async def test_in_memory_cache_basic_crud():
    cache = InMemoryCacheService()

    # 1. Miss returns None
    assert await cache.get("key1") is None

    # 2. Set and hit
    await cache.set("key1", {"message": "hello"}, ttl_seconds=60)
    val = await cache.get("key1")
    assert val == {"message": "hello"}

    # 3. Delete
    await cache.delete("key1")
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_in_memory_cache_ttl_expiration():
    cache = InMemoryCacheService()

    # Set with 0.05s TTL
    await cache.set("quick_key", "value", ttl_seconds=0.05)
    assert await cache.get("quick_key") == "value"

    # Wait for expiration
    await asyncio.sleep(0.08)
    assert await cache.get("quick_key") is None


@pytest.mark.asyncio
async def test_in_memory_cache_clear_prefix():
    cache = InMemoryCacheService()

    await cache.set("transcript:vid1:en", "trans_en")
    await cache.set("transcript:vid1:es", "trans_es")
    await cache.set("transcript:vid2:en", "other_vid")
    await cache.set("other:key", "data")

    # Clear prefix for vid1
    await cache.clear_prefix("transcript:vid1:")

    assert await cache.get("transcript:vid1:en") is None
    assert await cache.get("transcript:vid1:es") is None
    assert await cache.get("transcript:vid2:en") == "other_vid"
    assert await cache.get("other:key") == "data"


@pytest.mark.asyncio
async def test_cache_stampede_single_flight():
    cache = InMemoryCacheService()
    execution_count = 0

    async def expensive_computation() -> str:
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.05)  # Simulate network latency
        return "expensive_result"

    # Launch 5 concurrent requests for the same key
    results = await asyncio.gather(
        cache.get_or_compute("single_flight_key", expensive_computation, ttl_seconds=60),
        cache.get_or_compute("single_flight_key", expensive_computation, ttl_seconds=60),
        cache.get_or_compute("single_flight_key", expensive_computation, ttl_seconds=60),
        cache.get_or_compute("single_flight_key", expensive_computation, ttl_seconds=60),
        cache.get_or_compute("single_flight_key", expensive_computation, ttl_seconds=60),
    )

    # All 5 callers get the exact same result
    assert all(r == "expensive_result" for r in results)
    # The expensive computation was called exactly ONCE (single-flight locking)
    assert execution_count == 1


class MockKVNamespace:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def get(self, key: str, type: str | None = None) -> Any:
        return self.storage.get(key)

    async def put(self, key: str, value: str, expirationTtl: int | None = None) -> None:
        self.storage[key] = value

    async def delete(self, key: str) -> None:
        self.storage.pop(key, None)


@pytest.mark.asyncio
async def test_kv_cache_service():
    mock_kv = MockKVNamespace()
    cache = KVCacheService(mock_kv)

    # Miss
    assert await cache.get("kv_key") is None

    # Put and Get
    await cache.set("kv_key", {"data": 42}, ttl_seconds=300)
    res = await cache.get("kv_key")
    assert res == {"data": 42}

    # Delete
    await cache.delete("kv_key")
    assert await cache.get("kv_key") is None
