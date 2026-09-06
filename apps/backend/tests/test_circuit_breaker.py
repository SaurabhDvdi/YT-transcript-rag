"""Tests for circuit breaker resilience and provider fallback."""

import time

import pytest

from src.services.generation.providers.mock import MockLLMProvider
from src.services.generation.router import LLMRouter
from src.services.resilience.circuit_breaker import CircuitBreaker, ProviderHealthTracker


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)

    # 1. Initially CLOSED
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True

    # 2. First failure
    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True

    # 3. Second failure reaches threshold -> OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False

    # 4. Wait for cooldown -> HALF_OPEN
    time.sleep(0.12)
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"

    # 5. Success in HALF_OPEN resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True


def test_circuit_breaker_half_open_failure():
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
    cb.record_failure()
    assert cb.state == "OPEN"

    time.sleep(0.06)
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"

    # Failure in HALF_OPEN trips back to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_llm_router_circuit_breaker_fallback():
    tracker = ProviderHealthTracker(failure_threshold=2, cooldown_seconds=60.0)

    p1 = MockLLMProvider()
    p1.name = "primary_mock"
    p2 = MockLLMProvider()
    p2.name = "secondary_mock"

    router = LLMRouter(p1, fallback_provider=p2, health_tracker=tracker)

    # Initially selects primary
    selected = router.select_provider()
    assert selected.name == "primary_mock"

    # Trip the circuit for primary
    tracker.record_outcome("primary_mock", success=False)
    tracker.record_outcome("primary_mock", success=False)

    assert not tracker.is_available("primary_mock")

    # Router should now gracefully skip primary and select secondary
    fallback = router.select_provider()
    assert fallback.name == "secondary_mock"
