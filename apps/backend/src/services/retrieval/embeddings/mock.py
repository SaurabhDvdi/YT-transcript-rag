"""Configurable mock embedding provider for tests."""


class MockEmbeddingProvider:
    """Configurable mock embedding provider for unit tests."""

    def __init__(self, dimensions: int = 384) -> None:
        self._dimensions = dimensions
        self._canned_vectors: dict[str, list[float]] = {}
        self._should_fail = False

    @property
    def name(self) -> str:
        return "mock-embedding-provider"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def set_should_fail(self, fail: bool) -> None:
        self._should_fail = fail

    def set_canned_vector(self, text: str, vector: list[float]) -> None:
        self._canned_vectors[text] = list(vector)

    def _generate_vector(self, text: str) -> list[float]:
        if self._should_fail:
            raise RuntimeError("MockEmbeddingProvider simulated failure")

        if text in self._canned_vectors:
            return list(self._canned_vectors[text])

        vec = [0.0] * self._dimensions
        h = 0
        for ch in text:
            h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
        idx = h % self._dimensions
        vec[idx] = 1.0
        return vec

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]
