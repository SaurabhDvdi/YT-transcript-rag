"""Cloudflare Workers AI embedding provider using @cf/baai/bge-small-en-v1.5 (384 dimensions)."""

import math
from typing import Any


class CloudflareAiEmbeddingProvider:
    """Cloudflare Workers AI embedding provider using @cf/baai/bge-small-en-v1.5."""

    def __init__(self, ai_binding: Any) -> None:
        if not ai_binding:
            raise ValueError("CloudflareAiBinding is required for CloudflareAiEmbeddingProvider")
        self._ai_binding = ai_binding
        self._model = "@cf/baai/bge-small-en-v1.5"

    @property
    def name(self) -> str:
        return "cloudflare-workers-ai"

    @property
    def dimensions(self) -> int:
        return 384

    def _normalize(self, vector: list[float]) -> list[float]:
        mag = math.sqrt(sum(x * x for x in vector))
        if mag == 0:
            return vector
        return [x / mag for x in vector]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        if not results:
            raise RuntimeError("No embedding returned from Cloudflare Workers AI")
        return results[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._ai_binding.run(self._model, {"text": texts})
        raw_vectors: list[list[float]] = []

        if isinstance(response, list):
            raw_vectors = response
        elif isinstance(response, dict) and "data" in response:
            data = response["data"]
            if isinstance(data, list) and data and isinstance(data[0], list):
                raw_vectors = data
            elif isinstance(data, list):
                # Flat list
                for i in range(0, len(data), self.dimensions):
                    raw_vectors.append(data[i : i + self.dimensions])
        else:
            raise RuntimeError("Unexpected response structure from Cloudflare Workers AI")

        return [self._normalize(v) for v in raw_vectors]
