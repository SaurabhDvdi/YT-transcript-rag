"""Manages an ordered chain of transcript providers with automated fallback."""

from src.core.errors import AppError
from src.services.transcript.types import (
    TranscriptOptions,
    TranscriptProvider,
    TranscriptResult,
)


class ProviderRegistry:
    """Chain-of-responsibility transcript provider registry."""

    def __init__(self, initial_providers: list[TranscriptProvider] | None = None) -> None:
        self._providers: list[TranscriptProvider] = list(initial_providers or [])

    def register_provider(self, provider: TranscriptProvider) -> None:
        self._providers.append(provider)

    def prepend_provider(self, provider: TranscriptProvider) -> None:
        self._providers.insert(0, provider)

    def get_providers(self) -> list[TranscriptProvider]:
        return list(self._providers)

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult:
        if not self._providers:
            raise AppError("INTERNAL_ERROR", 500, "No transcript providers registered in registry.")

        last_error: Exception | None = None
        any_temporary_failure = False

        for provider in self._providers:
            try:
                result = await provider.get_transcript(video_id, options)
                return result
            except AppError as err:
                last_error = err
                if err.code == "PROVIDER_TEMPORARY_FAILURE":
                    any_temporary_failure = True
                continue
            except Exception as err:
                last_error = err
                continue

        if isinstance(last_error, AppError):
            if any_temporary_failure and last_error.code != "PROVIDER_TEMPORARY_FAILURE":
                raise AppError(
                    "PROVIDER_TEMPORARY_FAILURE",
                    502,
                    "All transcript providers failed or were temporarily unreachable.",
                )
            raise last_error

        raise AppError(
            "CAPTIONS_UNAVAILABLE",
            404,
            "No accessible transcript could be retrieved from any provider.",
        )
