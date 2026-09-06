"""Configurable mock LLM provider for zero-cost offline development and deterministic unit testing."""

import re
from collections.abc import AsyncIterator

from src.core.errors import AppError
from src.services.generation.types import (
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMStreamChunk,
)


class MockLLMProvider:
    """Configurable mock LLM provider for tests and local development."""

    def __init__(self) -> None:
        self.name: str = "mock-llm"
        self.model: str = "mock-model-v1"
        self._default_response: str = "This is a grounded answer based on evidence. [E1]"
        self._response_map: dict[str, str] = {}
        self._custom_stream_chunks: list[str] | None = None
        self._transient_failures: int = 0
        self._permanent_failure: bool = False
        self._simulate_timeout: bool = False
        self.recorded_requests: list[LLMGenerationRequest] = []

    def set_default_response(self, text: str) -> None:
        self._default_response = text

    def set_response_for_keyword(self, keyword: str, response: str) -> None:
        self._response_map[keyword.lower()] = response

    def set_custom_stream_chunks(self, chunks: list[str] | None) -> None:
        self._custom_stream_chunks = chunks

    def set_transient_failures(self, count: int) -> None:
        self._transient_failures = count

    def set_permanent_failure(self, fail: bool) -> None:
        self._permanent_failure = fail

    def set_simulate_timeout(self, timeout: bool) -> None:
        self._simulate_timeout = timeout

    def clear_recorded_requests(self) -> None:
        self.recorded_requests.clear()

    setDefaultResponse = set_default_response
    setResponseForKeyword = set_response_for_keyword
    setCustomStreamChunks = set_custom_stream_chunks
    setTransientFailures = set_transient_failures
    setPermanentFailure = set_permanent_failure
    setSimulateTimeout = set_simulate_timeout

    def _resolve_text(self, request: LLMGenerationRequest) -> str:
        chosen_text = self._default_response
        user_p = request.user_prompt
        last_q_index = max(
            user_p.rfind("CURRENT QUESTION:"),
            user_p.rfind("Question:"),
        )
        target_text = user_p[last_q_index:].lower() if last_q_index != -1 else user_p.lower()

        for kw, resp in self._response_map.items():
            if kw in target_text:
                chosen_text = resp
                break

        return chosen_text

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        self.recorded_requests.append(request)

        if self._simulate_timeout:
            raise AppError("LLM_TIMEOUT", 504, "Mock LLM request timed out")

        if self._permanent_failure:
            raise AppError("INVALID_QUESTION", 400, "Mock LLM permanent caller error")

        if self._transient_failures > 0:
            self._transient_failures -= 1
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                "Mock LLM simulated transient 503 error",
            )

        chosen_text = self._resolve_text(request)

        return LLMGenerationResponse(
            text=chosen_text,
            provider=self.name,
            model=self.model,
            input_tokens=100,
            output_tokens=50,
            finish_reason="STOP",
        )

    async def stream(self, request: LLMGenerationRequest) -> AsyncIterator[LLMStreamChunk]:
        self.recorded_requests.append(request)

        if self._simulate_timeout:
            raise AppError("LLM_TIMEOUT", 504, "Mock LLM streaming timed out")

        if self._permanent_failure:
            raise AppError("INVALID_QUESTION", 400, "Mock LLM permanent caller error")

        if self._transient_failures > 0:
            self._transient_failures -= 1
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                "Mock LLM simulated transient 503 error",
            )

        text = self._resolve_text(request)
        if self._custom_stream_chunks is not None:
            chunks = self._custom_stream_chunks
        else:
            chunks = [c for c in re.split(r"(\s+)", text) if c]

        for i, chunk in enumerate(chunks):
            yield LLMStreamChunk(
                text=chunk,
                is_finished=(i == len(chunks) - 1),
            )
