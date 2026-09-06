"""Deterministic query rewriter resolving conversational follow-ups and pronouns."""

import re

from src.schemas.conversation import ConversationMessage

STOP_WORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
}


class DeterministicQueryRewriter:
    """Fast, deterministic query rewriter for conversational follow-ups.
    Resolves conversational pronouns and references without external LLM inference cost.
    """

    def _extract_subject(self, history: list[ConversationMessage]) -> str | None:
        if not history:
            return None

        # Look backwards for the most recent user question
        for msg in reversed(history):
            if msg.role == "user":
                text = msg.content.strip()

                # Pattern 1: What is / What are / Who is / Tell me about [Subject]
                question_pattern = re.compile(
                    r"(?:what\s+(?:is|are|was|were)|who\s+(?:is|was|introduced|created)|explain|tell\s+me\s+about|how\s+(?:does|do))\s+([^?.!,;]+)",
                    re.IGNORECASE,
                )
                match = question_pattern.search(text)
                if match and match.group(1):
                    raw_subject = match.group(1).strip()
                    clean_subject = self._clean_subject(raw_subject)
                    if len(clean_subject) > 1:
                        return clean_subject

                # Pattern 2: Fallback to non-stopword sequence
                cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
                words = [w for w in cleaned.split() if w.lower() not in STOP_WORDS and len(w) > 2]
                if words:
                    return " ".join(words[:3])

        return None

    def _clean_subject(self, raw: str) -> str:
        s = re.sub(r"^(?:the|a|an)\s+", "", raw, flags=re.IGNORECASE)
        s = re.sub(r"\s+(?:mean|work|function|operate)$", "", s, flags=re.IGNORECASE)
        return s.strip()

    async def rewrite(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        trimmed = question.strip()
        if not history:
            return trimmed

        lower = trimmed.lower()
        subject = self._extract_subject(history)
        if not subject:
            return trimmed

        # Exact matches
        if lower in ("why?", "why"):
            return f"Why is {subject} useful?"
        if lower in ("when?", "when", "when was it introduced?"):
            return f"When was {subject} introduced?"
        if lower in ("who?", "who", "who proposed it?", "who introduced it?"):
            return f"Who introduced {subject}?"
        if lower in ("how?", "how"):
            return f"How does {subject} work?"
        if lower.startswith("can you explain that more simply") or lower.startswith(
            "explain that simply"
        ):
            return f"Explain {subject} simply"

        # Pronoun replacement: "it", "that", "this"
        pronoun_regex = re.compile(r"\b(it|that|this)\b", re.IGNORECASE)
        if pronoun_regex.search(trimmed):
            return pronoun_regex.sub(subject, trimmed, count=1)

        # If question starts with "Why is it..." or "What does that mean..."
        if re.match(r"^(?:what\s+does\s+that\s+mean|what\s+is\s+that)", trimmed, re.IGNORECASE):
            return f"What is {subject}?"

        return trimmed
