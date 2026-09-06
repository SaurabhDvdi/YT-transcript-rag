"""Generation data models and schemas."""

from typing import Any, Literal

from src.schemas.base import CamelModel


class Citation(CamelModel):
    chunk_id: str
    start: float
    end: float
    score: float | None = None


class GroundedAnswer(CamelModel):
    text: str
    grounded: bool
    citations: list[Citation]
    message_id: str | None = None
    model: str = "gemini-1.5-flash"


class AssistantMessageSummary(CamelModel):
    id: str
    role: Literal["assistant"] = "assistant"
    text: str
    grounded: bool
    citations: list[Citation]
    created_at: str | None = None


class AskQuestionRequest(CamelModel):
    question: str
    conversation_id: str | None = None
    client_request_id: str | None = None
    top_k: int = 5


class AskQuestionResponse(CamelModel):
    success: bool = True
    video_id: str
    conversation_id: str | None = None
    answer: GroundedAnswer
    message: AssistantMessageSummary | None = None
    request_id: str | None = None


# Typed Streaming Protocol (SSE)
class StreamStartEvent(CamelModel):
    type: Literal["start"] = "start"
    request_id: str
    conversation_id: str
    message_id: str


class StreamTokenEvent(CamelModel):
    type: Literal["token"] = "token"
    text: str


class StreamCitationEvent(CamelModel):
    type: Literal["citation"] = "citation"
    citation: Citation


class StreamDoneEvent(CamelModel):
    type: Literal["done"] = "done"
    message: Any  # ConversationMessage


class StreamErrorEvent(CamelModel):
    type: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = (
    StreamStartEvent | StreamTokenEvent | StreamCitationEvent | StreamDoneEvent | StreamErrorEvent
)

# Aliases for compatibility
StartStreamEvent = StreamStartEvent
TokenStreamEvent = StreamTokenEvent
CitationStreamEvent = StreamCitationEvent
DoneStreamEvent = StreamDoneEvent
ErrorStreamEvent = StreamErrorEvent
