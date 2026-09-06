"""Videos API endpoints for registration, status, transcript, retrieval, conversations, and Q&A."""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.errors import AppError
from src.repositories.usage import D1UsageRepository
from src.schemas.conversation import (
    ConversationListResponse,
    CreateConversationResponse,
)
from src.schemas.generation import (
    AskQuestionResponse,
    AssistantMessageSummary,
)
from src.schemas.retrieval import RetrievalResponse
from src.schemas.transcript import TranscriptResponse
from src.schemas.video import (
    VideoAnalyzeResponse,
    VideoRecordSummary,
    VideoStatusResponse,
    is_valid_youtube_video_id,
)
from src.services.conversation.service import ConversationService
from src.services.generation.service import GenerationService
from src.services.generation.sse_encoder import encode_sse
from src.services.generation.types import GenerationOptions
from src.services.quota.limiter import PersistentUsageLimiter
from src.services.rate_limit.limiter import DistributedRateLimiter
from src.services.retrieval.service import RetrievalService
from src.services.transcript.service import TranscriptService

router = APIRouter(prefix="/api/v1/videos", tags=["Videos"])

# Global rate limiter instance for active stream concurrency tracking
_global_rate_limiter = DistributedRateLimiter()


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _get_session_id(request: Request) -> str:
    return getattr(request.state, "session_id", "default-session")


def _get_user_id(request: Request) -> str | None:
    """Return authenticated user_id or None for anonymous requests."""
    return getattr(request.state, "user_id", None) or None


def _get_limiter(request: Request) -> PersistentUsageLimiter:
    db = getattr(request.state, "db", None)
    repo = D1UsageRepository(db) if db else None
    return PersistentUsageLimiter(repo)


def _get_conversation_service(request: Request) -> ConversationService:
    db = getattr(request.state, "db", None)
    return ConversationService.get_instance(db)


def _validate_video_id(video_id: str) -> str:
    if not is_valid_youtube_video_id(video_id):
        raise AppError("INVALID_VIDEO_ID", 400, "The supplied YouTube video ID is invalid.")
    return video_id.strip()


@router.post("", response_model=VideoAnalyzeResponse, status_code=202)
@router.post("/", response_model=VideoAnalyzeResponse, status_code=202, include_in_schema=False)
async def analyze_video(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise AppError("INVALID_REQUEST", 400, "Content-Type must be application/json.")

    try:
        body = await request.json()
    except Exception:
        raise AppError("INVALID_REQUEST", 400, "Malformed or missing JSON body.") from None

    if not isinstance(body, dict) or "videoId" not in body:
        raise AppError("INVALID_REQUEST", 400, "Missing required 'videoId' in request body.")

    raw_video_id = body.get("videoId")
    if not isinstance(raw_video_id, str):
        raise AppError("INVALID_VIDEO_ID", 400, "The supplied YouTube video ID is invalid.")

    clean_video_id = _validate_video_id(raw_video_id)
    request_id = _get_request_id(request)
    session_id = _get_session_id(request)
    user_id = _get_user_id(request)

    # 1. Quota check before expensive video processing
    limiter = _get_limiter(request)
    decision = await limiter.check_quota(session_id, "process_video", user_id=user_id)
    if not decision.allowed:
        raise AppError(
            "QUOTA_EXCEEDED", 429, decision.reason or "Daily video processing quota reached."
        )

    db = getattr(request.state, "db", None)
    transcript_service = TranscriptService.get_instance(db)
    record = transcript_service.process_video(clean_video_id)
    retrieval_status = RetrievalService.get_instance(db).get_status(clean_video_id)

    await limiter.record_usage(
        session_id, "video_registered", video_id=clean_video_id, user_id=user_id
    )

    resp = VideoAnalyzeResponse(
        success=True,
        video=VideoRecordSummary(video_id=clean_video_id, status=record.status),
        transcript=record.summary,
        retrieval_status=retrieval_status,
        request_id=request_id,
    )
    return JSONResponse(status_code=202, content=resp.model_dump(by_alias=True, exclude_none=True))


@router.get("/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str, request: Request) -> VideoStatusResponse:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    db = getattr(request.state, "db", None)

    transcript_service = TranscriptService.get_instance(db)
    record = await transcript_service.get_record_async(clean_video_id)
    retrieval_status = RetrievalService.get_instance(db).get_status(clean_video_id)

    return VideoStatusResponse(
        success=True,
        video=VideoRecordSummary(
            video_id=clean_video_id,
            status=record.status if record else "accepted",
        ),
        transcript=record.summary if record else None,
        retrieval_status=retrieval_status,
        request_id=request_id,
    )


@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(video_id: str, request: Request) -> TranscriptResponse:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    db = getattr(request.state, "db", None)

    transcript_service = TranscriptService.get_instance(db)
    transcript = await transcript_service.get_transcript_async(clean_video_id)
    return TranscriptResponse(
        success=True,
        video_id=clean_video_id,
        transcript=transcript,
        request_id=request_id,
    )


@router.post("/{video_id}/retrieval", response_model=RetrievalResponse)
async def query_video_retrieval(video_id: str, request: Request) -> RetrievalResponse:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    db = getattr(request.state, "db", None)

    record = await TranscriptService.get_instance(db).get_record_async(clean_video_id)
    if not record:
        raise AppError(
            "NOT_FOUND",
            404,
            f"Video {clean_video_id} has not been registered. Register it via POST /api/v1/videos first.",
        )

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise AppError("INVALID_REQUEST", 400, "Content-Type must be application/json.")

    try:
        body = await request.json()
    except Exception:
        raise AppError("INVALID_REQUEST", 400, "Malformed or missing JSON body.") from None

    if not isinstance(body, dict) or "query" not in body:
        raise AppError("INVALID_QUERY", 400, "Missing required 'query' in request body.")

    query = body.get("query")
    if not isinstance(query, str) or not query.strip():
        raise AppError("INVALID_QUERY", 400, "Query must be a non-empty string.")

    top_k: int = 5
    if "topK" in body and body["topK"] is not None:
        raw_top_k = body["topK"]
        if not isinstance(raw_top_k, int) or raw_top_k < 1 or raw_top_k > 20:
            raise AppError("INVALID_TOP_K", 400, "topK must be an integer between 1 and 20.")
        top_k = raw_top_k

    results = await RetrievalService.get_instance(db).search(clean_video_id, query.strip(), top_k)
    return RetrievalResponse(
        success=True,
        video_id=clean_video_id,
        results=results,
        request_id=request_id,
    )


@router.post(
    "/{video_id}/conversations", response_model=CreateConversationResponse, status_code=201
)
async def create_video_conversation(video_id: str, request: Request) -> CreateConversationResponse:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    user_id = _get_user_id(request)

    conv_service = _get_conversation_service(request)
    session_id = _get_session_id(request)
    conv = await conv_service.create_conversation(
        clean_video_id, user_id=user_id, session_id=session_id
    )
    return CreateConversationResponse(
        success=True,
        conversation=conv,
        request_id=request_id,
    )


@router.get("/{video_id}/conversations", response_model=ConversationListResponse)
async def list_video_conversations(
    video_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> ConversationListResponse:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    user_id = _get_user_id(request)

    conv_service = _get_conversation_service(request)
    convs = await conv_service.list_conversations(clean_video_id, limit, user_id=user_id)
    return ConversationListResponse(
        success=True,
        video_id=clean_video_id,
        conversations=convs,
        request_id=request_id,
    )


@router.post("/{video_id}/ask", response_model=AskQuestionResponse)
async def ask_video_question(
    video_id: str,
    request: Request,
    stream: bool = Query(default=False),
) -> Response:
    clean_video_id = _validate_video_id(video_id)
    request_id = _get_request_id(request)
    session_id = _get_session_id(request)
    user_id = _get_user_id(request)

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise AppError("INVALID_REQUEST", 400, "Content-Type must be application/json.")

    try:
        body = await request.json()
    except Exception:
        raise AppError("INVALID_REQUEST", 400, "Malformed or missing JSON body.") from None

    if not isinstance(body, dict) or "question" not in body:
        raise AppError("INVALID_QUESTION", 400, "Missing required 'question' in request body.")

    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        raise AppError("INVALID_QUESTION", 400, "Question must be a non-empty string.")

    top_k: int = 5
    if "topK" in body and body["topK"] is not None:
        raw_top_k = body["topK"]
        if not isinstance(raw_top_k, int) or raw_top_k < 1 or raw_top_k > 10:
            raise AppError("INVALID_TOP_K", 400, "topK must be an integer between 1 and 10.")
        top_k = raw_top_k

    conversation_id: str | None = None
    if "conversationId" in body and body["conversationId"] is not None:
        raw_cid = body["conversationId"]
        if not isinstance(raw_cid, str) or not raw_cid.strip():
            raise AppError(
                "INVALID_CONVERSATION_ID", 400, "conversationId must be a non-empty string."
            )
        conversation_id = raw_cid.strip()

    client_request_id: str | None = None
    if "clientRequestId" in body and body["clientRequestId"] is not None:
        raw_crid = body["clientRequestId"]
        if not isinstance(raw_crid, str) or not raw_crid.strip():
            raise AppError("INVALID_REQUEST", 400, "clientRequestId must be a non-empty string.")
        client_request_id = raw_crid.strip()

    # 1. Quota check for questions
    limiter = _get_limiter(request)
    decision = await limiter.check_quota(session_id, "ask", user_id=user_id)
    if not decision.allowed:
        raise AppError("QUOTA_EXCEEDED", 429, decision.reason or "Daily question quota reached.")

    # 2. Conversation ownership guard if conversation_id was passed
    if conversation_id:
        conv = await _get_conversation_service(request).validate_conversation_for_video(
            conversation_id, clean_video_id
        )
        from src.api.routes.conversations import _assert_ownership

        _assert_ownership(conv, user_id)

    # 3. Verify video is registered
    db = getattr(request.state, "db", None)
    transcript_service = TranscriptService.get_instance(db)
    record = await transcript_service.get_record_async(clean_video_id)
    if not record:
        raise AppError(
            "NOT_FOUND",
            404,
            f"Video {clean_video_id} has not been registered. Register it via POST /api/v1/videos first.",
        )

    # 4. Verify retrieval is ready
    retrieval_service = RetrievalService.get_instance(db)
    retrieval_status = retrieval_service.get_status(clean_video_id)
    if retrieval_status != "ready" and await retrieval_service.get_vector_store().has_video(
        clean_video_id
    ):
        retrieval_status = "ready"
        retrieval_service.set_status(clean_video_id, "ready")

    if retrieval_status != "ready":
        raise AppError(
            "RETRIEVAL_NOT_READY",
            409,
            f"Video retrieval index is not ready yet (current status: {retrieval_status}).",
        )

    generation_service = GenerationService.get_instance()
    options = GenerationOptions(
        top_k=top_k,
        conversation_id=conversation_id,
        client_request_id=client_request_id,
    )

    # 5. Enforce stream concurrency limits
    if stream:
        acquired = await _global_rate_limiter.acquire_stream(session_id, max_concurrent=1)
        if not acquired:
            raise AppError(
                "CONCURRENT_STREAM_LIMIT_EXCEEDED",
                429,
                "An active generation stream is already in progress for this session.",
            )

        async def event_generator() -> AsyncIterator[str]:
            try:
                async for event in generation_service.stream_answer_question(
                    clean_video_id, question.strip(), options
                ):
                    yield encode_sse(event)
                await limiter.record_usage(
                    session_id, "generation_succeeded", video_id=clean_video_id, user_id=user_id
                )
            except Exception:
                await limiter.record_usage(
                    session_id, "generation_failed", video_id=clean_video_id, user_id=user_id
                )
                raise
            finally:
                await _global_rate_limiter.release_stream(session_id)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )

    # Non-streaming ask
    try:
        result = await generation_service.answer_question(clean_video_id, question.strip(), options)
        await limiter.record_usage(
            session_id, "generation_succeeded", video_id=clean_video_id, user_id=user_id
        )
    except Exception:
        await limiter.record_usage(
            session_id, "generation_failed", video_id=clean_video_id, user_id=user_id
        )
        raise

    message_summary: AssistantMessageSummary | None = None
    if result.message_id:
        message_summary = AssistantMessageSummary(
            id=result.message_id,
            role="assistant",
            text=result.text,
            grounded=result.grounded,
            citations=result.citations,
        )

    resp = AskQuestionResponse(
        success=True,
        video_id=clean_video_id,
        conversation_id=conversation_id,
        answer=result.to_grounded_answer(),
        message=message_summary,
        request_id=request_id,
    )
    return JSONResponse(status_code=200, content=resp.model_dump(by_alias=True, exclude_none=True))
