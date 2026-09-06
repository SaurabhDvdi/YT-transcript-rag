"""Query rewriter protocol for conversational follow-ups."""

from typing import Protocol

from src.schemas.conversation import ConversationMessage


class QueryRewriter(Protocol):
    """Interface for rewriting conversational follow-up queries into self-contained retrieval queries."""

    async def rewrite(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str: ...
