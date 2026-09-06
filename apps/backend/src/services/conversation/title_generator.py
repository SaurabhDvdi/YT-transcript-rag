"""Deterministic conversation title generator (<= 50 chars)."""

import re

LEADING_FLUFF_PATTERNS = [
    re.compile(
        r"^(can|could|would|will)\s+you\s+(please\s+)?(tell\s+me|explain|describe|clarify|summarize|give\s+me|outline)\s+(about\s+)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(please\s+)?(tell\s+me|explain|describe|clarify|summarize|give\s+me|outline)\s+(about\s+)?",
        re.IGNORECASE,
    ),
    re.compile(r"^(what\s+is|what\s+are|what\s+was|what\s+were|what's)\s+(the\s+)?", re.IGNORECASE),
    re.compile(r"^(why\s+is|why\s+are|why\s+does|why\s+do|why\s+did|why)\s+", re.IGNORECASE),
    re.compile(
        r"^(how\s+does|how\s+do|how\s+is|how\s+are|how\s+to|how\s+can|how)\s+", re.IGNORECASE
    ),
    re.compile(r"^(who\s+is|who\s+was|who\s+are|who\s+were)\s+", re.IGNORECASE),
    re.compile(r"^(where\s+is|where\s+are|when\s+was|when\s+did)\s+", re.IGNORECASE),
    re.compile(r"^(in\s+this\s+video|according\s+to\s+(the\s+)?video)\s*,?\s*", re.IGNORECASE),
    re.compile(r"^(can\s+you|could\s+you)\s+", re.IGNORECASE),
]

MAX_TITLE_LENGTH = 50

MINOR_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "for",
    "nor",
    "on",
    "at",
    "to",
    "by",
    "in",
    "of",
    "vs",
    "is",
    "than",
}

SCRIPT_TAG_REGEX = re.compile(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.IGNORECASE)
HTML_TAG_REGEX = re.compile(r"<[^>]*>")
QUOTES_REGEX = re.compile(r"[\"'`“”‘’]")
PUNCTUATION_STRIP_REGEX = re.compile(r"[?.!,:;~-]+$")


def _capitalize_sub_token(token: str, is_first_word: bool) -> str:
    lower = token.lower()
    if len(token) >= 2 and token == token.upper() and token.isalnum():
        return token
    if not is_first_word and lower in MINOR_WORDS:
        return lower
    return lower.capitalize()


def _to_title_case(s: str) -> str:
    words = s.split()
    res: list[str] = []
    for word_idx, word in enumerate(words):
        if "-" in word:
            parts = word.split("-")
            capped_parts = [
                _capitalize_sub_token(part, word_idx == 0 and part_idx == 0)
                for part_idx, part in enumerate(parts)
            ]
            res.append("-".join(capped_parts))
        else:
            res.append(_capitalize_sub_token(word, word_idx == 0))
    return " ".join(res)


def generate_conversation_title(raw_question: str) -> str:
    """Generates a clean, concise title from a user question."""
    if not raw_question or not isinstance(raw_question, str):
        return "New Conversation"

    # 1. Strip script tags and HTML tags
    text = SCRIPT_TAG_REGEX.sub("", raw_question)
    text = HTML_TAG_REGEX.sub("", text)
    text = QUOTES_REGEX.sub("", text)
    text = re.sub(r"[\r\n\t]+", " ", text).strip()

    if not text:
        return "New Conversation"

    # 2. Strip leading conversational fluff patterns iteratively
    modified = True
    while modified:
        modified = False
        for pattern in LEADING_FLUFF_PATTERNS:
            if pattern.search(text):
                text = pattern.sub("", text).strip()
                modified = True

    # 3. Strip trailing punctuation
    text = PUNCTUATION_STRIP_REGEX.sub("", text).strip()

    if not text:
        return "General Discussion"

    # 4. Convert to Title Case
    title = _to_title_case(text)

    # 5. Enforce <= 50 characters budget gracefully at word boundary
    if len(title) > MAX_TITLE_LENGTH:
        truncated = title[:MAX_TITLE_LENGTH]
        last_space = truncated.rfind(" ")
        title = truncated[:last_space] if last_space > 20 else truncated

    title = PUNCTUATION_STRIP_REGEX.sub("", title).strip()
    return title if title else "New Conversation"


generate_title_from_query = generate_conversation_title
