"""Type definitions and protocols for LLM text generation and context building."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from src.schemas.generation import Citation, GroundedAnswer
from src.schemas.retrieval import RetrievalChunk


@dataclass
class LLMGenerationRequest:
    """Normalized input request passed to any LLMProvider."""

    system_prompt: str
    user_prompt: str
    max_output_tokens: int
    temperature: float


@dataclass
class LLMGenerationResponse:
    """Normalized response envelope returned by any LLMProvider."""

    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


@dataclass
class LLMStreamChunk:
    """Normalized streaming chunk yielded by streaming-capable LLMProviders."""

    text: str
    is_finished: bool = False


@runtime_checkable
class LLMProvider(Protocol):
    """Pluggable provider interface for LLM text generation."""

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse: ...

    def stream(self, request: LLMGenerationRequest) -> AsyncIterator[LLMStreamChunk]: ...


@dataclass
class AIConfig:
    """Centralized AI provider routing and model configuration."""

    default_provider: str
    fallback_provider: str | None = None
    max_output_tokens: int = 1024
    temperature: float = 0.2
    timeout_ms: int = 15000


@dataclass
class GenerationOptions:
    """Options passed to GenerationService for an individual question."""

    top_k: int = 5
    conversation_id: str | None = None
    client_request_id: str | None = None
    timeout_ms: int = 15000


@dataclass
class GenerationContext:
    """Evidence context package prepared by ContextBuilder."""

    has_evidence: bool
    evidence_count: int
    formatted_context: str
    evidence_chunks: list[RetrievalChunk] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Answer with citations and optional saved message ID."""

    text: str
    grounded: bool
    citations: list[Citation] = field(default_factory=list)
    message_id: str | None = None

    def to_grounded_answer(self) -> GroundedAnswer:
        return GroundedAnswer(
            text=self.text,
            grounded=self.grounded,
            citations=self.citations,
        )
