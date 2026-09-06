"""Conversation data models and schemas."""

from typing import Literal

from src.schemas.base import CamelModel
from src.schemas.generation import Citation

MessageRole = Literal["user", "assistant"]
TitleSource = Literal["auto", "user"]


class Conversation(CamelModel):
    id: str
    video_id: str
    title: str = "New Conversation"
    title_source: TitleSource = "auto"
    created_at: str
    updated_at: str
    user_id: str | None = None  # None = anonymous conversation
    session_id: str | None = None


class ConversationSummary(CamelModel):
    id: str
    video_id: str
    title: str = "New Conversation"
    title_source: TitleSource = "auto"
    created_at: str
    updated_at: str
    user_id: str | None = None
    session_id: str | None = None


class ConversationMessage(CamelModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    citations: list[Citation] | None = None
    grounded: bool | None = None
    client_request_id: str | None = None
    created_at: str


class CreateConversationResponse(CamelModel):
    success: bool = True
    conversation: Conversation
    request_id: str | None = None


class ConversationListResponse(CamelModel):
    success: bool = True
    video_id: str
    conversations: list[Conversation]
    request_id: str | None = None


class ConversationDetailResponse(CamelModel):
    success: bool = True
    conversation: Conversation
    messages: list[ConversationMessage]
    request_id: str | None = None


class ConversationMessagesResponse(CamelModel):
    success: bool = True
    conversation_id: str
    messages: list[ConversationMessage]
    next_cursor: str | None = None
    request_id: str | None = None


class ConversationUpdateRequest(CamelModel):
    title: str
    video_id: str | None = None


class ConversationUpdateResponse(CamelModel):
    success: bool = True
    conversation: Conversation
    request_id: str | None = None


class ConversationDeleteResponse(CamelModel):
    success: bool = True
    conversation_id: str
    request_id: str | None = None
