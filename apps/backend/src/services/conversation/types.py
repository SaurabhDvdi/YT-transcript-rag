"""Conversation repository protocols and paginated results."""

from dataclasses import dataclass
from typing import Protocol

from src.schemas.conversation import Conversation, ConversationMessage, TitleSource


@dataclass
class PaginatedMessages:
    messages: list[ConversationMessage]
    next_cursor: str | None = None


class ConversationRepository(Protocol):
    async def create(
        self,
        video_id: str,
        id_or_title: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Conversation: ...

    async def get_by_id(self, conversation_id: str) -> Conversation | None: ...

    async def list_by_video(
        self, video_id: str, limit: int = 20, user_id: str | None = None
    ) -> list[Conversation]: ...

    async def update_timestamp(
        self, conversation_id: str, updated_at: str | None = None
    ) -> None: ...

    async def update_title(
        self, conversation_id: str, title: str, source: TitleSource
    ) -> Conversation | None: ...

    async def delete(self, conversation_id: str) -> None: ...


class MessageRepository(Protocol):
    async def add(self, message: ConversationMessage) -> None: ...

    async def get_by_client_request_id(
        self, client_request_id: str
    ) -> ConversationMessage | None: ...

    async def list_recent(self, conversation_id: str, limit: int) -> list[ConversationMessage]: ...

    async def list_with_cursor(
        self, conversation_id: str, limit: int, cursor: str | None = None
    ) -> PaginatedMessages: ...
