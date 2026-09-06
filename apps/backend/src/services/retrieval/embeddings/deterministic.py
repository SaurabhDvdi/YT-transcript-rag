"""Deterministic 384-dimensional embedding provider matching TypeScript bit-for-bit."""

import math
import re

ALPHANUM_REGEX = re.compile(r"[^a-z0-9]")


def hash_string(s: str, seed: int = 0x811C9DC5) -> int:
    """Fast 32-bit FNV-1a hash with seed."""
    h = seed
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class DeterministicEmbeddingProvider:
    """Deterministic, offline, zero-cost 384-dimensional embedding provider."""

    @property
    def name(self) -> str:
        return "deterministic"

    @property
    def dimensions(self) -> int:
        return 384

    def generate_vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        cleaned = text.lower().strip()
        if not cleaned:
            return vector

        words = cleaned.split()

        for raw_word in words:
            word = ALPHANUM_REGEX.sub("", raw_word)
            if not word:
                continue

            # Full word token feature (weight = 2.0)
            word_hash = hash_string(word)
            word_idx = word_hash % self.dimensions
            word_sign = 1.0 if (hash_string(word, 0x12345678) & 1) == 1 else -1.0
            vector[word_idx] += 2.0 * word_sign

            # Character 3-grams
            for i in range(len(word) - 2):
                tri = word[i : i + 3]
                tri_hash = hash_string(tri)
                tri_idx = tri_hash % self.dimensions
                tri_sign = 1.0 if (hash_string(tri, 0x9E3779B9) & 1) == 1 else -1.0
                vector[tri_idx] += 1.0 * tri_sign

            # Character 4-grams
            for i in range(len(word) - 3):
                quad = word[i : i + 4]
                quad_hash = hash_string(quad)
                quad_idx = quad_hash % self.dimensions
                quad_sign = 1.0 if (hash_string(quad, 0x85EBCA6B) & 1) == 1 else -1.0
                vector[quad_idx] += 1.2 * quad_sign

        # L2 Normalization
        sum_squares = sum(x * x for x in vector)
        magnitude = math.sqrt(sum_squares)
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    async def embed_query(self, text: str) -> list[float]:
        return self.generate_vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.generate_vector(t) for t in texts]
