"""Conversations API routes for metadata, pagination, renaming, and deletion."""

import re

from fastapi import APIRouter, Query, Request

from src.core.errors import AppError
from src.schemas.conversation import (
    ConversationDeleteResponse,
    ConversationDetailResponse,
    ConversationMessagesResponse,
    ConversationUpdateResponse,
)
from src.services.conversation.service import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _get_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or None


def _get_conversation_service(request: Request) -> ConversationService:
    db = getattr(request.state, "db", None)
    return ConversationService.get_instance(db)


def _assert_ownership(conv: object, caller_user_id: str | None) -> None:
    """Assert that the caller owns the conversation.

    Rules:
    - Authenticated user: conversation must have matching user_id
    - Anonymous caller: conversation must have no user_id (NULL)
    """
    from src.schemas.conversation import Conversation

    if not isinstance(conv, Conversation):
        return
    conv_user_id: str | None = getattr(conv, "user_id", None)
    if caller_user_id is not None:
        # Authenticated path: must match
        if conv_user_id != caller_user_id:
            raise AppError(
                "CONVERSATION_FORBIDDEN", 403, "You do not have access to this conversation."
            )
    else:
        # Anonymous path: conversation must also be ownerless
        if conv_user_id is not None:
            raise AppError(
                "CONVERSATION_FORBIDDEN", 403, "You do not have access to this conversation."
            )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    request: Request,
) -> ConversationDetailResponse:
    clean_id = conversation_id.strip()
    if not clean_id:
        raise AppError("INVALID_CONVERSATION_ID", 400, "Conversation ID is required.")

    service = _get_conversation_service(request)
    conv = await service.get_conversation(clean_id)
    if not conv:
        raise AppError("CONVERSATION_NOT_FOUND", 404, f"Conversation {clean_id} was not found.")
    _assert_ownership(conv, _get_user_id(request))

    messages = await service.get_recent_messages(clean_id, limit=20)
    return ConversationDetailResponse(
        success=True,
        conversation=conv,
        messages=messages,
        request_id=_get_request_id(request),
    )


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> ConversationMessagesResponse:
    clean_id = conversation_id.strip()
    if not clean_id:
        raise AppError("INVALID_CONVERSATION_ID", 400, "Conversation ID is required.")

    service = _get_conversation_service(request)
    conv = await service.get_conversation(clean_id)
    if not conv:
        raise AppError("CONVERSATION_NOT_FOUND", 404, f"Conversation {clean_id} was not found.")
    _assert_ownership(conv, _get_user_id(request))

    paginated = await service.get_messages_with_cursor(clean_id, limit=limit, cursor=cursor)
    return ConversationMessagesResponse(
        success=True,
        conversation_id=clean_id,
        messages=paginated.messages,
        next_cursor=paginated.next_cursor,
        request_id=_get_request_id(request),
    )


@router.patch("/{conversation_id}", response_model=ConversationUpdateResponse)
async def update_conversation_title(
    conversation_id: str,
    request: Request,
    video_id: str | None = Query(default=None, alias="videoId"),
) -> ConversationUpdateResponse:
    clean_id = conversation_id.strip()
    if not clean_id:
        raise AppError("INVALID_CONVERSATION_ID", 400, "Conversation ID is required.")

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise AppError("INVALID_REQUEST", 400, "Content-Type must be application/json.")

    try:
        body = await request.json()
    except Exception:
        raise AppError("INVALID_REQUEST", 400, "Malformed JSON request body.") from None

    if not isinstance(body, dict) or "title" not in body:
        raise AppError("INVALID_REQUEST", 400, "Missing required 'title' field.")

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        raise AppError("INVALID_REQUEST", 400, "Title must be a non-empty string.")

    clean_title = title.strip()
    if len(clean_title) > 100:
        raise AppError("INVALID_REQUEST", 400, "Title must not exceed 100 characters.")

    if re.search(r"<[^>]*>", clean_title):
        raise AppError("INVALID_REQUEST", 400, "Title contains invalid HTML characters.")

    body_video_id = body.get("videoId")
    video_id_filter = (
        body_video_id.strip()
        if isinstance(body_video_id, str) and body_video_id.strip()
        else video_id
    )

    service = _get_conversation_service(request)

    # Ownership check: verify the conversation belongs to this user/session
    caller_user_id = _get_user_id(request)
    conv = await service.get_conversation(clean_id)
    if not conv:
        raise AppError("CONVERSATION_NOT_FOUND", 404, f"Conversation {clean_id} was not found.")
    _assert_ownership(conv, caller_user_id)

    updated = await service.update_conversation_title(
        clean_id,
        clean_title,
        "user",
        video_id_filter,
    )

    return ConversationUpdateResponse(
        success=True,
        conversation=updated,
        request_id=_get_request_id(request),
    )


@router.delete("/{conversation_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    video_id: str | None = Query(default=None, alias="videoId"),
) -> ConversationDeleteResponse:
    clean_id = conversation_id.strip()
    if not clean_id:
        raise AppError("INVALID_CONVERSATION_ID", 400, "Conversation ID is required.")

    service = _get_conversation_service(request)

    # Ownership check
    caller_user_id = _get_user_id(request)
    conv = await service.get_conversation(clean_id)
    if not conv:
        raise AppError("CONVERSATION_NOT_FOUND", 404, f"Conversation {clean_id} was not found.")
    _assert_ownership(conv, caller_user_id)

    await service.delete_conversation(clean_id, video_id)

    return ConversationDeleteResponse(
        success=True,
        conversation_id=clean_id,
        request_id=_get_request_id(request),
    )
