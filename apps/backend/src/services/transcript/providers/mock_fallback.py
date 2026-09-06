"""Mock transcript provider for tests and offline development."""

from src.core.errors import AppError
from src.schemas.transcript import TranscriptSegment
from src.services.transcript.types import CaptionTrackSource, TranscriptOptions, TranscriptResult


class MockFallbackProvider:
    """Configurable mock provider for test suites and offline local development."""

    def __init__(self, generate_defaults: bool = True) -> None:
        self._mock_responses: dict[str, TranscriptResult] = {}
        self._mock_errors: dict[str, AppError] = {}
        self.generate_defaults = generate_defaults

    @property
    def name(self) -> str:
        return "mock-fallback"

    def set_mock_response(self, video_id: str, result: TranscriptResult) -> None:
        self._mock_responses[video_id] = result

    def set_mock_error(self, video_id: str, error: AppError) -> None:
        self._mock_errors[video_id] = error

    def clear_mocks(self) -> None:
        self._mock_responses.clear()
        self._mock_errors.clear()

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult:
        if video_id in self._mock_errors:
            raise self._mock_errors[video_id]

        if video_id in self._mock_responses:
            return self._mock_responses[video_id]

        if self.generate_defaults:
            return TranscriptResult(
                video_id=video_id,
                language="English",
                language_code="en",
                is_auto_generated=False,
                total_duration=60.0,
                segments=[
                    TranscriptSegment(
                        index=0,
                        start=0.0,
                        duration=30.0,
                        end=30.0,
                        text="This video discusses system architecture, attention mechanisms, and key concepts.",
                    ),
                    TranscriptSegment(
                        index=1,
                        start=30.0,
                        duration=30.0,
                        end=60.0,
                        text="We examine machine learning algorithms, embeddings, and vector search.",
                    ),
                ],
                source=CaptionTrackSource(
                    provider=self.name,
                    language_code="en",
                    is_auto_generated=False,
                ),
            )

        raise AppError(
            "TRANSCRIPT_NOT_FOUND",
            404,
            f"No mock transcript registered for video {video_id}",
        )
