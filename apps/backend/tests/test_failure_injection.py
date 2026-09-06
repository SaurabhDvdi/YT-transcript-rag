"""Tests for fault injection, graceful degradation, and error recovery."""

from collections.abc import AsyncIterator

import pytest

from src.repositories.video import InMemoryVideoRepository
from src.schemas.video import VideoRecord
from src.services.generation.providers.mock import MockLLMProvider
from src.services.generation.router import LLMRouter
from src.services.generation.types import (
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMProvider,
    LLMStreamChunk,
)
from src.services.rate_limit.limiter import DistributedRateLimiter
from src.services.resilience.circuit_breaker import ProviderHealthTracker


class FailingLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "failing_provider"

    @property
    def model(self) -> str:
        return "failing-model"

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        raise RuntimeError("Simulated external provider crash (503 Service Unavailable)")

    async def stream(self, request: LLMGenerationRequest) -> AsyncIterator[LLMStreamChunk]:
        raise RuntimeError("Simulated stream timeout")
        yield  # type: ignore


@pytest.mark.asyncio
async def test_video_status_error_handling():
    video_repo = InMemoryVideoRepository()
    await video_repo.save(VideoRecord(video_id="faulty_vid", status="processing"))

    # Simulate transcript failure
    updated = await video_repo.update_status(
        "faulty_vid",
        status="error",
        transcript_status="error",
        error_message="YouTube transcript blocked by bot detection",
    )
    assert updated is not None
    assert updated.status == "error"
    assert updated.transcript_status == "error"
    assert "bot detection" in (updated.error_message or "")


@pytest.mark.asyncio
async def test_llm_provider_failover_under_fault():
    tracker = ProviderHealthTracker(failure_threshold=1, cooldown_seconds=60.0)

    bad_p = FailingLLMProvider()
    good_p = MockLLMProvider()

    router = LLMRouter(bad_p, fallback_provider=good_p, health_tracker=tracker)

    # First attempt: selects bad provider
    p = router.select_provider()
    assert p.name == "failing_provider"

    # Trip the circuit for bad provider
    req = LLMGenerationRequest(
        system_prompt="sys", user_prompt="usr", max_output_tokens=100, temperature=0.0
    )
    try:
        await p.generate(req)
    except RuntimeError:
        tracker.record_outcome("failing_provider", success=False)

    # Next attempt: router automatically routes around broken provider to good provider
    fallback_p = router.select_provider()
    assert fallback_p.name == "mock-llm"
    res = await fallback_p.generate(req)
    assert len(res.text) > 0


@pytest.mark.asyncio
async def test_stream_resource_leak_prevention():
    limiter = DistributedRateLimiter()
    session_id = "fault_session_stream"

    # Acquire stream
    acquired = await limiter.acquire_stream(session_id, max_concurrent=1)
    assert acquired is True

    # Simulate exception during streaming and verify release_stream cleans up state
    try:
        raise ValueError("Unexpected streaming client abort")
    except ValueError:
        await limiter.release_stream(session_id)

    # After cleanup, next stream should succeed without being blocked by phantom stream
    reacquired = await limiter.acquire_stream(session_id, max_concurrent=1)
    assert reacquired is True
    await limiter.release_stream(session_id)
