"""LLM provider router with timeout management and bounded single fallback."""

import asyncio
from collections.abc import AsyncIterator

from src.core.constants import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_PROVIDER_TIMEOUT_MS,
    DEFAULT_TEMPERATURE,
)
from src.core.errors import AppError
from src.services.generation.types import (
    AIConfig,
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMProvider,
    LLMStreamChunk,
)
from src.services.resilience.circuit_breaker import ProviderHealthTracker


def is_transient_failure(err: Exception) -> bool:
    """Checks whether an error represents a transient provider failure eligible for fallback."""
    if isinstance(err, AppError):
        return err.code in (
            "LLM_PROVIDER_UNAVAILABLE",
            "LLM_TIMEOUT",
            "LLM_PROVIDER_ERROR",
        ) or err.status_code in (
            502,
            503,
            504,
            429,
        )
    return False


class LLMRouter:
    """Provider router orchestrating primary provider execution with bounded 1-attempt fallback."""

    def __init__(
        self,
        primary_provider: LLMProvider,
        fallback_provider: LLMProvider | None = None,
        config: AIConfig | None = None,
        health_tracker: ProviderHealthTracker | None = None,
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.config = config or AIConfig(
            default_provider=primary_provider.name,
            fallback_provider=fallback_provider.name if fallback_provider else None,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=DEFAULT_TEMPERATURE,
            timeout_ms=DEFAULT_PROVIDER_TIMEOUT_MS,
        )
        self.health_tracker = health_tracker or ProviderHealthTracker.get_instance()

    def get_primary_provider(self) -> LLMProvider:
        return self.primary_provider

    def get_fallback_provider(self) -> LLMProvider | None:
        return self.fallback_provider

    def select_provider(self) -> LLMProvider:
        """Returns the currently active healthy provider (primary if available, else fallback)."""
        if self.health_tracker.is_available(self.primary_provider.name):
            return self.primary_provider
        if self.fallback_provider and self.health_tracker.is_available(self.fallback_provider.name):
            return self.fallback_provider
        return self.primary_provider

    def get_config(self) -> AIConfig:
        return self.config

    async def generate(
        self,
        request: LLMGenerationRequest,
        timeout_ms: int | None = None,
    ) -> LLMGenerationResponse:
        """Executes generation with timeout protection, circuit breaker, and bounded single fallback."""
        effective_timeout = (timeout_ms or self.config.timeout_ms) / 1000.0

        # Check circuit breaker on primary
        if not self.health_tracker.is_available(self.primary_provider.name):
            if self.fallback_provider:
                try:
                    async with asyncio.timeout(effective_timeout):
                        res = await self.fallback_provider.generate(request)
                        self.health_tracker.record_outcome(self.fallback_provider.name, True)
                        return res
                except Exception as fb_err:
                    self.health_tracker.record_outcome(self.fallback_provider.name, False)
                    raise fb_err from None
            raise AppError(
                "LLM_PROVIDER_ERROR",
                503,
                f"Primary provider {self.primary_provider.name} is temporarily unavailable.",
            )

        try:
            try:
                async with asyncio.timeout(effective_timeout):
                    res = await self.primary_provider.generate(request)
                    self.health_tracker.record_outcome(self.primary_provider.name, True)
                    return res
            except TimeoutError:
                self.health_tracker.record_outcome(self.primary_provider.name, False)
                raise AppError("LLM_TIMEOUT", 504, "Primary LLM request timed out") from None
        except Exception as primary_err:
            self.health_tracker.record_outcome(self.primary_provider.name, False)
            if self.fallback_provider and is_transient_failure(primary_err):
                try:
                    async with asyncio.timeout(effective_timeout):
                        res = await self.fallback_provider.generate(request)
                        self.health_tracker.record_outcome(self.fallback_provider.name, True)
                        return res
                except TimeoutError:
                    self.health_tracker.record_outcome(self.fallback_provider.name, False)
                    raise AppError("LLM_TIMEOUT", 504, "Fallback LLM request timed out") from None
                except Exception as fallback_err:
                    self.health_tracker.record_outcome(self.fallback_provider.name, False)
                    if isinstance(fallback_err, AppError):
                        raise fallback_err
                    raise primary_err from None
            raise primary_err

    async def stream(
        self,
        request: LLMGenerationRequest,
        timeout_ms: int | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Executes streaming generation with bounded single fallback."""
        effective_timeout = (timeout_ms or self.config.timeout_ms) / 1000.0

        try:
            # Try primary streaming
            if hasattr(self.primary_provider, "stream"):
                try:
                    async with asyncio.timeout(effective_timeout):
                        async for chunk in self.primary_provider.stream(request):
                            yield chunk
                    return
                except TimeoutError:
                    raise AppError("LLM_TIMEOUT", 504, "Primary LLM streaming timed out") from None
                except Exception as primary_err:
                    if self.fallback_provider and is_transient_failure(primary_err):
                        if hasattr(self.fallback_provider, "stream"):
                            async with asyncio.timeout(effective_timeout):
                                async for chunk in self.fallback_provider.stream(request):
                                    yield chunk
                            return
                        # Fallback lacks stream: generate text and yield as single chunk
                        resp = await self.fallback_provider.generate(request)
                        yield LLMStreamChunk(text=resp.text, is_finished=True)
                        return
                    raise primary_err
            elif self.fallback_provider and hasattr(self.fallback_provider, "stream"):
                async with asyncio.timeout(effective_timeout):
                    async for chunk in self.fallback_provider.stream(request):
                        yield chunk
                return
            else:
                resp = await self.generate(request, timeout_ms=timeout_ms)
                yield LLMStreamChunk(text=resp.text, is_finished=True)
        except (AppError, GeneratorExit):
            raise
        except TimeoutError:
            raise AppError("LLM_TIMEOUT", 504, "Streaming request timed out") from None
