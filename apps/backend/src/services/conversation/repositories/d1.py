"""Cloudflare D1 SQL database repositories for conversations and messages."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from src.schemas.conversation import Conversation, ConversationMessage, TitleSource
from src.schemas.generation import Citation
from src.services.conversation.types import PaginatedMessages


class D1ConversationRepository:
    """Cloudflare D1 repository for conversations table."""

    def __init__(self, db: Any) -> None:
        self.db = db

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
        stmt = self.db.prepare(
            "INSERT INTO conversations (id, video_id, user_id, session_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        ).bind(cid, video_id, user_id, session_id, now, now)
        await stmt.run()

        if title != "New Conversation":
            await self.update_title(cid, title, "auto")

        return Conversation(
            id=cid,
            video_id=video_id,
            title=title,
            title_source="auto",
            created_at=now,
            updated_at=now,
            user_id=user_id,
            session_id=session_id,
        )

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        stmt = self.db.prepare(
            "SELECT id, video_id, title, title_source, created_at, updated_at, user_id, session_id FROM conversations WHERE id = ?"
        ).bind(conversation_id)
        row = await stmt.first()
        if not row:
            return None

        # Convert JS object or dict
        r = dict(row) if hasattr(row, "__getitem__") else getattr(row, "__dict__", {})
        return Conversation(
            id=r.get("id", ""),
            video_id=r.get("video_id", ""),
            title=r.get("title") or "New Conversation",
            title_source=r.get("title_source") or "auto",
            created_at=r.get("created_at", ""),
            updated_at=r.get("updated_at", ""),
            user_id=r.get("user_id"),
            session_id=r.get("session_id"),
        )

    async def list_by_video(
        self, video_id: str, limit: int = 20, user_id: str | None = None
    ) -> list[Conversation]:
        safe_limit = max(1, min(limit, 100))
        if user_id is not None:
            # Authenticated: show only this user's conversations
            stmt = self.db.prepare(
                "SELECT id, video_id, title, title_source, created_at, updated_at, user_id, session_id FROM conversations "
                "WHERE video_id = ? AND user_id = ? ORDER BY updated_at DESC LIMIT ?"
            ).bind(video_id, user_id, safe_limit)
        else:
            # Anonymous: show only conversations without an owner
            stmt = self.db.prepare(
                "SELECT id, video_id, title, title_source, created_at, updated_at, user_id, session_id FROM conversations "
                "WHERE video_id = ? AND user_id IS NULL ORDER BY updated_at DESC LIMIT ?"
            ).bind(video_id, safe_limit)
        res = await stmt.all()
        results = (
            getattr(res, "results", None)
            or (res.get("results") if isinstance(res, dict) else [])
            or []
        )

        conversations: list[Conversation] = []
        for row in results:
            r = dict(row) if hasattr(row, "__getitem__") else getattr(row, "__dict__", {})
            conversations.append(
                Conversation(
                    id=r.get("id", ""),
                    video_id=r.get("video_id", ""),
                    title=r.get("title") or "New Conversation",
                    title_source=r.get("title_source") or "auto",
                    created_at=r.get("created_at", ""),
                    updated_at=r.get("updated_at", ""),
                    user_id=r.get("user_id"),
                    session_id=r.get("session_id"),
                )
            )
        return conversations

    async def update_timestamp(self, conversation_id: str, updated_at: str | None = None) -> None:
        timestamp = updated_at or datetime.now(UTC).isoformat()
        stmt = self.db.prepare("UPDATE conversations SET updated_at = ? WHERE id = ?").bind(
            timestamp, conversation_id
        )
        await stmt.run()

    async def update_title(
        self, conversation_id: str, title: str, source: TitleSource
    ) -> Conversation | None:
        now = datetime.now(UTC).isoformat()
        stmt = self.db.prepare(
            "UPDATE conversations SET title = ?, title_source = ?, updated_at = ? WHERE id = ?"
        ).bind(title, source, now, conversation_id)
        await stmt.run()
        return await self.get_by_id(conversation_id)

    async def delete(self, conversation_id: str) -> None:
        stmt = self.db.prepare("DELETE FROM conversations WHERE id = ?").bind(conversation_id)
        await stmt.run()


class D1MessageRepository:
    """Cloudflare D1 repository for messages table."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def _map_row(self, row: Any) -> ConversationMessage:
        r = dict(row) if hasattr(row, "__getitem__") else getattr(row, "__dict__", {})
        raw_cites = r.get("citations")
        citations: list[Citation] | None = None
        if raw_cites and isinstance(raw_cites, str):
            try:
                parsed = json.loads(raw_cites)
                if isinstance(parsed, list):
                    citations = [Citation.model_validate(c) for c in parsed]
            except Exception:
                citations = None

        raw_grounded = r.get("grounded")
        grounded = True if raw_grounded == 1 else False if raw_grounded == 0 else None

        return ConversationMessage(
            id=r.get("id", ""),
            conversation_id=r.get("conversation_id", ""),
            role=r.get("role", "user"),
            content=r.get("content", ""),
            citations=citations,
            grounded=grounded,
            client_request_id=r.get("client_request_id"),
            created_at=r.get("created_at", ""),
        )

    async def add(self, message: ConversationMessage) -> None:
        citations_json = (
            json.dumps([c.model_dump(by_alias=True) for c in message.citations])
            if message.citations
            else None
        )
        grounded_int = 1 if message.grounded is True else 0 if message.grounded is False else None

        stmt = self.db.prepare(
            "INSERT INTO messages (id, conversation_id, role, content, citations, grounded, client_request_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(
            message.id,
            message.conversation_id,
            message.role,
            message.content,
            citations_json,
            grounded_int,
            message.client_request_id,
            message.created_at,
        )
        await stmt.run()

    async def get_by_client_request_id(self, client_request_id: str) -> ConversationMessage | None:
        stmt = self.db.prepare(
            "SELECT id, conversation_id, role, content, citations, grounded, client_request_id, created_at FROM messages WHERE client_request_id = ?"
        ).bind(client_request_id)
        row = await stmt.first()
        return self._map_row(row) if row else None

    async def list_recent(self, conversation_id: str, limit: int) -> list[ConversationMessage]:
        safe_limit = max(1, min(limit, 100))
        stmt = self.db.prepare(
            """SELECT id, conversation_id, role, content, citations, grounded, client_request_id, created_at
            FROM (
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            )
            ORDER BY created_at ASC"""
        ).bind(conversation_id, safe_limit)
        res = await stmt.all()
        results = (
            getattr(res, "results", None)
            or (res.get("results") if isinstance(res, dict) else [])
            or []
        )
        return [self._map_row(r) for r in results]

    async def list_with_cursor(
        self, conversation_id: str, limit: int, cursor: str | None = None
    ) -> PaginatedMessages:
        safe_limit = max(1, min(limit, 100))
        if cursor:
            stmt = self.db.prepare(
                """SELECT id, conversation_id, role, content, citations, grounded, client_request_id, created_at
                FROM messages
                WHERE conversation_id = ? AND created_at > ?
                ORDER BY created_at ASC
                LIMIT ?"""
            ).bind(conversation_id, cursor, safe_limit + 1)
        else:
            stmt = self.db.prepare(
                """SELECT id, conversation_id, role, content, citations, grounded, client_request_id, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?"""
            ).bind(conversation_id, safe_limit + 1)

        res = await stmt.all()
        results = (
            getattr(res, "results", None)
            or (res.get("results") if isinstance(res, dict) else [])
            or []
        )
        has_more = len(results) > safe_limit
        slice_items = results[:safe_limit]
        mapped = [self._map_row(r) for r in slice_items]
        next_cursor = mapped[-1].created_at if has_more and mapped else None

        return PaginatedMessages(messages=mapped, next_cursor=next_cursor)

    async def delete_by_conversation_id(self, conversation_id: str) -> None:
        stmt = self.db.prepare("DELETE FROM messages WHERE conversation_id = ?").bind(
            conversation_id
        )
        await stmt.run()
