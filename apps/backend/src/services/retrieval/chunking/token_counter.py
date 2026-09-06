"""Heuristic token counter matching TypeScript logic."""

import math
import re

PUNCTUATION_REGEX = re.compile(r"[.,!?;:\"'()[\]{}/*\-+—_@#$%^&=<>~`]")


class HeuristicTokenCounter:
    """Fast, deterministic token counter heuristic approximating subword BPE tokenization."""

    def count_tokens(self, text: str) -> int:
        trimmed = text.strip()
        if not trimmed:
            return 0

        words = trimmed.split()
        token_estimate = 0

        for word in words:
            punct_count = len(PUNCTUATION_REGEX.findall(word))
            alphanumeric = PUNCTUATION_REGEX.sub("", word)

            word_tokens = 1
            if len(alphanumeric) > 6:
                word_tokens = math.ceil(len(alphanumeric) / 4.0)

            token_estimate += word_tokens + punct_count

        return max(1, token_estimate)
