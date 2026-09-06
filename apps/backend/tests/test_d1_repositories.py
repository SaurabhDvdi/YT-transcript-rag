"""Tests for D1 repository implementation against real SQL schema and migrations."""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from src.schemas.conversation import ConversationMessage
from src.schemas.generation import Citation
from src.services.conversation.repositories.d1 import (
    D1ConversationRepository,
    D1MessageRepository,
)


class MockD1Statement:
    def __init__(self, conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()):
        self.conn = conn
        self.sql = sql
        self.params = params

    def bind(self, *params: Any) -> "MockD1Statement":
        return MockD1Statement(self.conn, self.sql, params)

    async def run(self) -> dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute(self.sql, self.params)
        self.conn.commit()
        return {"success": True, "meta": {"changes": cursor.rowcount}}

    async def first(self, col: str | None = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute(self.sql, self.params)
        row = cursor.fetchone()
        if not row:
            return None
        col_names = [d[0] for d in cursor.description]
        data = dict(zip(col_names, row, strict=False))
        return data if col is None else data.get(col)

    async def all(self) -> dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute(self.sql, self.params)
        rows = cursor.fetchall()
        col_names = [d[0] for d in cursor.description]
        results = [dict(zip(col_names, r, strict=False)) for r in rows]
        return {"results": results, "success": True}


class MockD1Database:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def prepare(self, sql: str) -> MockD1Statement:
        return MockD1Statement(self.conn, sql)


@pytest.fixture
def d1_db() -> MockD1Database:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        conn.executescript(migration_file.read_text(encoding="utf-8"))
    return MockD1Database(conn)


@pytest.mark.asyncio
async def test_d1_conversation_repository_crud(d1_db: MockD1Database):
    repo = D1ConversationRepository(d1_db)
    video_id = "test_vid_123"

    # 1. Create conversation
    conv = await repo.create(video_id=video_id, id_or_title="My Topic")
    assert conv.video_id == video_id
    assert conv.title == "My Topic"
    assert conv.title_source == "auto"

    # 2. Get by ID
    fetched = await repo.get_by_id(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id
    assert fetched.title == "My Topic"

    # 3. Update title
    updated = await repo.update_title(conv.id, "Renamed Topic", "user")
    assert updated.title == "Renamed Topic"
    assert updated.title_source == "user"

    # 4. List by video
    conv_list = await repo.list_by_video(video_id)
    assert len(conv_list) == 1
    assert conv_list[0].id == conv.id

    # 5. Delete conversation
    await repo.delete(conv.id)
    assert await repo.get_by_id(conv.id) is None


@pytest.mark.asyncio
async def test_d1_message_repository_persistence_and_citations(d1_db: MockD1Database):
    conv_repo = D1ConversationRepository(d1_db)
    msg_repo = D1MessageRepository(d1_db)
    conv = await conv_repo.create(video_id="test_vid_citations")
    now = datetime.now(UTC).isoformat()

    # 1. Add User message
    user_msg = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content="What is self-attention?",
        client_request_id="req-12345",
        created_at=now,
    )
    await msg_repo.add(user_msg)

    # 2. Add Assistant message with structured citations
    citations = [
        Citation(chunk_id="c1", start=10.5, end=25.0, score=0.92),
        Citation(chunk_id="c2", start=30.0, end=45.2, score=0.88),
    ]
    asst_msg = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="assistant",
        content="Self attention computes pairwise similarities [10:05 - 10:25].",
        citations=citations,
        grounded=True,
        created_at=now,
    )
    await msg_repo.add(asst_msg)

    # 3. Fetch recent messages
    recent = await msg_repo.list_recent(conv.id, limit=10)
    assert len(recent) == 2
    assert recent[0].role == "assistant"
    assert recent[1].role == "user"
    assert len(recent[0].citations or []) == 2
    assert (recent[0].citations or [])[0].start == 10.5

    # 4. Test cascade delete: deleting conversation removes all messages
    await conv_repo.delete(conv.id)
    messages_after_delete = await msg_repo.list_recent(conv.id, limit=10)
    assert len(messages_after_delete) == 0


@pytest.mark.asyncio
async def test_d1_client_request_id_idempotency(d1_db: MockD1Database):
    conv_repo = D1ConversationRepository(d1_db)
    msg_repo = D1MessageRepository(d1_db)
    conv = await conv_repo.create(video_id="test_vid_idempotent")
    now = datetime.now(UTC).isoformat()

    msg1 = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content="First attempt",
        client_request_id="unique-request-key-999",
        created_at=now,
    )
    await msg_repo.add(msg1)

    found = await msg_repo.get_by_client_request_id("unique-request-key-999")
    assert found is not None
    assert found.content == "First attempt"

    # Attempting to insert same client_request_id raises integrity error
    msg_duplicate = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content="Duplicate attempt",
        client_request_id="unique-request-key-999",
        created_at=now,
    )
    with pytest.raises(sqlite3.IntegrityError):
        await msg_repo.add(msg_duplicate)
