"""Auth repository protocol + D1 and InMemory implementations."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Domain models (plain dataclasses — not Pydantic to stay dependency-light)
# ---------------------------------------------------------------------------


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    password_salt: str
    created_at: str
    updated_at: str
    deleted_at: str | None = None


@dataclass
class AuthSession:
    id: str
    user_id: str
    token_hash: str
    expires_at: str
    created_at: str
    revoked_at: str | None = None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class AuthRepository(Protocol):
    async def create_user(self, email: str, password_hash: str, salt: str) -> User: ...

    async def get_user_by_email(self, email: str) -> User | None: ...

    async def get_user_by_id(self, user_id: str) -> User | None: ...

    async def soft_delete_user(self, user_id: str) -> None: ...

    async def create_session(
        self, user_id: str, token_hash: str, expires_at: str
    ) -> AuthSession: ...

    async def get_session_by_token_hash(self, token_hash: str) -> AuthSession | None: ...

    async def revoke_session(self, session_id: str) -> None: ...

    async def revoke_all_user_sessions(self, user_id: str) -> None: ...


# ---------------------------------------------------------------------------
# InMemory (unit-test / local-dev without D1)
# ---------------------------------------------------------------------------


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._sessions: dict[str, AuthSession] = {}

    async def create_user(self, email: str, password_hash: str, salt: str) -> User:
        now = datetime.now(UTC).isoformat()
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            password_salt=salt,
            created_at=now,
            updated_at=now,
        )
        self._users[user.id] = user
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        needle = email.lower().strip()
        for u in self._users.values():
            if u.email == needle:
                return u
        return None

    async def get_user_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    async def soft_delete_user(self, user_id: str) -> None:
        user = self._users.get(user_id)
        if user:
            user.deleted_at = datetime.now(UTC).isoformat()

    async def create_session(self, user_id: str, token_hash: str, expires_at: str) -> AuthSession:
        now = datetime.now(UTC).isoformat()
        session = AuthSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )
        self._sessions[session.id] = session
        return session

    async def get_session_by_token_hash(self, token_hash: str) -> AuthSession | None:
        for s in self._sessions.values():
            if s.token_hash == token_hash:
                return s
        return None

    async def revoke_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.revoked_at = datetime.now(UTC).isoformat()

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        for s in self._sessions.values():
            if s.user_id == user_id and s.revoked_at is None:
                s.revoked_at = now


# ---------------------------------------------------------------------------
# D1 (production Cloudflare Workers)
# ---------------------------------------------------------------------------


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Normalise a D1 result row to a plain dict."""
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "__dict__"):
        d = getattr(row, "__dict__", {})
        return dict(d) if isinstance(d, dict) else {}
    try:
        return dict(row)
    except Exception:
        return {}


class D1AuthRepository:
    def __init__(self, db: Any) -> None:
        self.db = db

    async def create_user(self, email: str, password_hash: str, salt: str) -> User:
        now = datetime.now(UTC).isoformat()
        user_id = str(uuid.uuid4())
        stmt = self.db.prepare(
            """
            INSERT INTO users (id, email, password_hash, password_salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        ).bind(user_id, email.lower().strip(), password_hash, salt, now, now)
        await stmt.run()
        return User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=password_hash,
            password_salt=salt,
            created_at=now,
            updated_at=now,
        )

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = self.db.prepare("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL").bind(
            email.lower().strip()
        )
        row = await stmt.first()
        if not row:
            return None
        d = _row_to_dict(row)
        return User(
            id=d["id"],
            email=d["email"],
            password_hash=d["password_hash"],
            password_salt=d["password_salt"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            deleted_at=d.get("deleted_at"),
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        stmt = self.db.prepare("SELECT * FROM users WHERE id = ?").bind(user_id)
        row = await stmt.first()
        if not row:
            return None
        d = _row_to_dict(row)
        return User(
            id=d["id"],
            email=d["email"],
            password_hash=d["password_hash"],
            password_salt=d["password_salt"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            deleted_at=d.get("deleted_at"),
        )

    async def soft_delete_user(self, user_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        stmt = self.db.prepare("UPDATE users SET deleted_at = ?, updated_at = ? WHERE id = ?").bind(
            now, now, user_id
        )
        await stmt.run()

    async def create_session(self, user_id: str, token_hash: str, expires_at: str) -> AuthSession:
        now = datetime.now(UTC).isoformat()
        session_id = str(uuid.uuid4())
        stmt = self.db.prepare(
            """
            INSERT INTO auth_sessions (id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """
        ).bind(session_id, user_id, token_hash, expires_at, now)
        await stmt.run()
        return AuthSession(
            id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )

    async def get_session_by_token_hash(self, token_hash: str) -> AuthSession | None:
        stmt = self.db.prepare(
            """
            SELECT * FROM auth_sessions
            WHERE token_hash = ? AND revoked_at IS NULL
            """
        ).bind(token_hash)
        row = await stmt.first()
        if not row:
            return None
        d = _row_to_dict(row)
        return AuthSession(
            id=d["id"],
            user_id=d["user_id"],
            token_hash=d["token_hash"],
            expires_at=d["expires_at"],
            created_at=d["created_at"],
            revoked_at=d.get("revoked_at"),
        )

    async def revoke_session(self, session_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        stmt = self.db.prepare("UPDATE auth_sessions SET revoked_at = ? WHERE id = ?").bind(
            now, session_id
        )
        await stmt.run()

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        stmt = self.db.prepare(
            "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL"
        ).bind(now, user_id)
        await stmt.run()
