"""In-memory repositories for conversations and messages."""

import uuid
from datetime import UTC, datetime

from src.schemas.conversation import Conversation, ConversationMessage, TitleSource
from src.services.conversation.types import PaginatedMessages


class InMemoryConversationRepository:
    """In-memory conversation repository for unit tests and local dev."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    async def create(
        self,
        video_id: str,
        id_or_title: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Conversation:
        title = "New Conversation"

        if conversation_id is not None:
            cid = conversation_id
            title = id_or_title or "New Conversation"
        elif id_or_title:
            if id_or_title.startswith("conv_") or len(id_or_title) == 36:
                cid = id_or_title
            else:
                cid = str(uuid.uuid4())
                title = id_or_title
        else:
            cid = str(uuid.uuid4())

        now = datetime.now(UTC).isoformat()
        conv = Conversation(
            id=cid,
            video_id=video_id,
            title=title,
            title_source="auto",
            created_at=now,
            updated_at=now,
            user_id=user_id,
            session_id=session_id,
        )
        self._conversations[cid] = conv
        return conv.model_copy()

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        conv = self._conversations.get(conversation_id)
        return conv.model_copy() if conv else None

    async def list_by_video(
        self, video_id: str, limit: int = 20, user_id: str | None = None
    ) -> list[Conversation]:
        if user_id is not None:
            filtered = [
                c
                for c in self._conversations.values()
                if c.video_id == video_id and c.user_id == user_id
            ]
        else:
            filtered = [
                c
                for c in self._conversations.values()
                if c.video_id == video_id and c.user_id is None
            ]
        filtered.sort(key=lambda c: c.updated_at, reverse=True)
        safe_limit = max(1, limit)
        return [c.model_copy() for c in filtered[:safe_limit]]

    async def update_timestamp(self, conversation_id: str, updated_at: str | None = None) -> None:
        conv = self._conversations.get(conversation_id)
        if conv:
            conv.updated_at = updated_at or datetime.now(UTC).isoformat()

    async def update_title(
        self, conversation_id: str, title: str, source: TitleSource
    ) -> Conversation | None:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None
        conv.title = title
        conv.title_source = source
        conv.updated_at = datetime.now(UTC).isoformat()
        return conv.model_copy()

    async def delete(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)

    async def reset(self) -> None:
        self._conversations.clear()


class InMemoryMessageRepository:
    """In-memory message repository for unit tests and local dev."""

    def __init__(self) -> None:
        self._messages: list[ConversationMessage] = []

    async def add(self, message: ConversationMessage) -> None:
        self._messages.append(message.model_copy())

    async def get_by_client_request_id(self, client_request_id: str) -> ConversationMessage | None:
        for m in self._messages:
            if m.client_request_id == client_request_id:
                return m.model_copy()
        return None

    async def list_recent(self, conversation_id: str, limit: int) -> list[ConversationMessage]:
        filtered = [m for m in self._messages if m.conversation_id == conversation_id]
        filtered.sort(key=lambda m: m.created_at)
        safe_limit = max(1, limit)
        recent = filtered[-safe_limit:]
        return [m.model_copy() for m in recent]

    async def list_with_cursor(
        self, conversation_id: str, limit: int, cursor: str | None = None
    ) -> PaginatedMessages:
        safe_limit = max(1, min(limit, 100))
        filtered = [m for m in self._messages if m.conversation_id == conversation_id]
        filtered.sort(key=lambda m: m.created_at)

        if cursor:
            filtered = [m for m in filtered if m.created_at > cursor]

        has_more = len(filtered) > safe_limit
        slice_items = filtered[:safe_limit]
        next_cursor = slice_items[-1].created_at if has_more and slice_items else None

        return PaginatedMessages(
            messages=[m.model_copy() for m in slice_items],
            next_cursor=next_cursor,
        )

    async def delete_by_conversation_id(self, conversation_id: str) -> None:
        self._messages = [m for m in self._messages if m.conversation_id != conversation_id]

    async def reset(self) -> None:
        self._messages.clear()
