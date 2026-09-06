"""Conversation service managing conversations and messages lifecycle."""

import uuid
from datetime import UTC, datetime
from typing import Any

from src.core.errors import AppError
from src.schemas.conversation import Conversation, ConversationMessage, TitleSource
from src.schemas.generation import Citation
from src.services.conversation.repositories.d1 import D1ConversationRepository, D1MessageRepository
from src.services.conversation.repositories.memory import (
    InMemoryConversationRepository,
    InMemoryMessageRepository,
)
from src.services.conversation.types import (
    ConversationRepository,
    MessageRepository,
    PaginatedMessages,
)


class ConversationService:
    """Service layer for managing conversations, messages, validation, and auto-titling."""

    _instance: "ConversationService | None" = None

    def __init__(
        self,
        conversation_repo: ConversationRepository | None = None,
        message_repo: MessageRepository | None = None,
    ) -> None:
        self.conversation_repo: ConversationRepository = (
            conversation_repo if conversation_repo is not None else InMemoryConversationRepository()
        )
        self.message_repo: MessageRepository = (
            message_repo if message_repo is not None else InMemoryMessageRepository()
        )

    @classmethod
    def get_instance(cls, db: Any = None) -> "ConversationService":
        if cls._instance is None:
            if db is not None:
                cls._instance = cls(
                    conversation_repo=D1ConversationRepository(db),
                    message_repo=D1MessageRepository(db),
                )
            else:
                cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "ConversationService | None") -> None:
        cls._instance = instance

    async def reset(self) -> None:
        if hasattr(self.conversation_repo, "reset") and callable(self.conversation_repo.reset):
            await self.conversation_repo.reset()
        if hasattr(self.message_repo, "reset") and callable(self.message_repo.reset):
            await self.message_repo.reset()

    async def create_conversation(
        self,
        video_id: str,
        title: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Conversation:
        """Create a new conversation for a video."""
        return await self.conversation_repo.create(
            video_id=video_id, id_or_title=title, user_id=user_id, session_id=session_id
        )

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get conversation metadata by ID."""
        return await self.conversation_repo.get_by_id(conversation_id)

    async def list_conversations(
        self, video_id: str, limit: int = 20, user_id: str | None = None
    ) -> list[Conversation]:
        """List conversations for a video ordered by updated_at descending."""
        return await self.conversation_repo.list_by_video(
            video_id=video_id, limit=limit, user_id=user_id
        )

    async def validate_conversation_for_video(
        self, conversation_id: str, video_id: str
    ) -> Conversation:
        """Validate that conversation exists and belongs to the video.

        Raises:
            AppError(CONVERSATION_NOT_FOUND, 404) if not found.
            AppError(CONVERSATION_VIDEO_MISMATCH, 400) if video_id does not match.
        """
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise AppError(
                code="CONVERSATION_NOT_FOUND",
                status_code=404,
                message=f"Conversation {conversation_id} not found",
            )
        if conversation.video_id != video_id:
            raise AppError(
                code="CONVERSATION_VIDEO_MISMATCH",
                status_code=400,
                message=f"Conversation {conversation_id} belongs to video {conversation.video_id}, not {video_id}",
            )
        return conversation

    async def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
        source: TitleSource,
        video_id: str | None = None,
    ) -> Conversation:
        """Update conversation title and titleSource."""
        if video_id:
            await self.validate_conversation_for_video(conversation_id, video_id)
        else:
            conv = await self.conversation_repo.get_by_id(conversation_id)
            if not conv:
                raise AppError(
                    code="CONVERSATION_NOT_FOUND",
                    status_code=404,
                    message=f"Conversation {conversation_id} not found",
                )

        updated = await self.conversation_repo.update_title(
            conversation_id=conversation_id,
            title=title,
            source=source,
        )
        if not updated:
            raise AppError(
                code="CONVERSATION_NOT_FOUND",
                status_code=404,
                message=f"Conversation {conversation_id} not found",
            )
        return updated

    async def delete_conversation(self, conversation_id: str, video_id: str | None = None) -> None:
        """Delete a conversation and associated messages."""
        if video_id:
            await self.validate_conversation_for_video(conversation_id, video_id)
        else:
            conv = await self.conversation_repo.get_by_id(conversation_id)
            if not conv:
                raise AppError(
                    code="CONVERSATION_NOT_FOUND",
                    status_code=404,
                    message=f"Conversation {conversation_id} not found",
                )

        await self.conversation_repo.delete(conversation_id)

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 10
    ) -> list[ConversationMessage]:
        """List recent messages in chronological order."""
        return await self.message_repo.list_recent(conversation_id, limit)

    async def get_messages_with_cursor(
        self, conversation_id: str, limit: int = 20, cursor: str | None = None
    ) -> PaginatedMessages:
        """List messages with cursor-based pagination."""
        return await self.message_repo.list_with_cursor(conversation_id, limit, cursor)

    async def get_message_by_client_request_id(
        self, client_request_id: str
    ) -> ConversationMessage | None:
        """Check idempotency by clientRequestId."""
        return await self.message_repo.get_by_client_request_id(client_request_id)

    async def add_user_message(
        self,
        conversation_id: str,
        content: str,
        client_request_id: str | None = None,
    ) -> ConversationMessage:
        """Append user message to conversation."""
        now = datetime.now(UTC).isoformat()
        message = ConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=content,
            client_request_id=client_request_id,
            created_at=now,
        )
        await self.message_repo.add(message)
        await self.conversation_repo.update_timestamp(conversation_id, message.created_at)
        return message

    async def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        citations: list[Citation] | None = None,
        grounded: bool | None = None,
    ) -> ConversationMessage:
        """Append assistant response to conversation."""
        now = datetime.now(UTC).isoformat()
        message = ConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            citations=citations or [],
            grounded=grounded if grounded is not None else True,
            created_at=now,
        )
        await self.message_repo.add(message)
        await self.conversation_repo.update_timestamp(conversation_id, message.created_at)
        return message
