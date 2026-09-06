"""Pytest fixtures and configuration."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from src.api.middleware import reset_rate_limit_store
from src.core.telemetry import TelemetryService
from src.main import app
from src.services.conversation.service import ConversationService
from src.services.generation.service import GenerationService
from src.services.job.service import JobService
from src.services.resilience.circuit_breaker import ProviderHealthTracker
from src.services.retrieval.service import RetrievalService
from src.services.transcript.service import TranscriptService


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
    """Provides a fresh SQLite in-memory D1 database with all migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        conn.executescript(sql_file.read_text(encoding="utf-8"))
    return MockD1Database(conn)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons and in-memory caches before each test."""
    reset_rate_limit_store()
    TelemetryService.get_instance().reset()
    ProviderHealthTracker.get_instance().reset()
    TranscriptService.set_instance(None)
    RetrievalService.set_instance(None)
    ConversationService.set_instance(None)
    GenerationService.set_instance(None)
    JobService.set_instance(None)
    from src.services.auth.service import AuthService

    AuthService.set_instance(None)

    yield

    reset_rate_limit_store()
    TelemetryService.get_instance().reset()
    ProviderHealthTracker.get_instance().reset()
    TranscriptService.set_instance(None)
    RetrievalService.set_instance(None)
    ConversationService.set_instance(None)
    GenerationService.set_instance(None)
    JobService.set_instance(None)
    AuthService.set_instance(None)


@pytest.fixture
def client():
    """Synchronous test client for simple endpoint tests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Asynchronous HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
