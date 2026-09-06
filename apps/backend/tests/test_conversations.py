"""Tests for conversation service, repositories, and title generator."""

import pytest

from src.core.errors import AppError
from src.services.conversation.service import ConversationService
from src.services.conversation.title_generator import generate_conversation_title


@pytest.mark.asyncio
async def test_conversation_lifecycle():
    service = ConversationService.get_instance()
    video_id = "abc123xyz89"

    # Create conversation
    conv = await service.create_conversation(video_id)
    assert conv.video_id == video_id
    assert conv.title == "New Conversation"
    assert conv.title_source == "auto"

    # Get by ID
    fetched = await service.get_conversation(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id

    # List conversations for video
    conv_list = await service.list_conversations(video_id)
    assert len(conv_list) == 1
    assert conv_list[0].id == conv.id

    # Update title
    updated = await service.update_conversation_title(conv.id, "Understanding Transformers", "user")
    assert updated.title == "Understanding Transformers"
    assert updated.title_source == "user"

    # Delete conversation
    await service.delete_conversation(conv.id)
    assert await service.get_conversation(conv.id) is None


@pytest.mark.asyncio
async def test_conversation_video_isolation():
    service = ConversationService.get_instance()
    conv = await service.create_conversation("video_A")

    # Correct video matches
    await service.validate_conversation_for_video(conv.id, "video_A")

    # Mismatched video raises 400
    with pytest.raises(AppError) as exc_info:
        await service.validate_conversation_for_video(conv.id, "video_B")
    assert exc_info.value.code == "CONVERSATION_VIDEO_MISMATCH"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_messages_cursor_pagination():
    service = ConversationService.get_instance()
    conv = await service.create_conversation("vid_pagination")

    for i in range(5):
        await service.add_user_message(conv.id, f"User message {i}")

    # Paginate with limit 2
    page1 = await service.get_messages_with_cursor(conv.id, limit=2)
    assert len(page1.messages) == 2
    assert page1.next_cursor is not None

    page2 = await service.get_messages_with_cursor(conv.id, limit=2, cursor=page1.next_cursor)
    assert len(page2.messages) == 2
    assert page2.next_cursor is not None


def test_title_generator_fluff_removal():
    title = generate_conversation_title("Can you please explain how self-attention works?")
    assert title == "Self-Attention Works"


def test_title_generator_length_bound():
    long_question = "What is the comprehensive overview of the theoretical foundations of modern quantum electrodynamics and thermodynamics in cosmological models?"
    title = generate_conversation_title(long_question)
    assert len(title) <= 50


@pytest.mark.asyncio
async def test_conversation_user_ownership_and_scoping():
    from src.api.routes.conversations import _assert_ownership

    service = ConversationService.get_instance()
    vid = "test_vid_ownership"

    # 1. Anonymous conversation
    anon_conv = await service.create_conversation(vid, title="Anon Chat", user_id=None)
    assert anon_conv.user_id is None

    # 2. User 1 conversation
    u1_conv = await service.create_conversation(vid, title="User 1 Chat", user_id="user_1")
    assert u1_conv.user_id == "user_1"

    # 3. User 2 conversation
    u2_conv = await service.create_conversation(vid, title="User 2 Chat", user_id="user_2")
    assert u2_conv.user_id == "user_2"

    # 4. Scoped listings
    anon_list = await service.list_conversations(vid, user_id=None)
    assert any(c.id == anon_conv.id for c in anon_list)
    assert not any(c.id == u1_conv.id for c in anon_list)
    assert not any(c.id == u2_conv.id for c in anon_list)

    u1_list = await service.list_conversations(vid, user_id="user_1")
    assert any(c.id == u1_conv.id for c in u1_list)
    assert not any(c.id == anon_conv.id for c in u1_list)
    assert not any(c.id == u2_conv.id for c in u1_list)

    # 5. Ownership assertion rules
    # Anon caller accessing anon conv -> Allowed
    _assert_ownership(anon_conv, caller_user_id=None)

    # User 1 caller accessing user 1 conv -> Allowed
    _assert_ownership(u1_conv, caller_user_id="user_1")

    # User 2 caller accessing user 1 conv -> Forbidden (403)
    with pytest.raises(AppError) as exc_info:
        _assert_ownership(u1_conv, caller_user_id="user_2")
    assert exc_info.value.code == "CONVERSATION_FORBIDDEN"
    assert exc_info.value.status_code == 403

    # Anon caller accessing user 1 conv -> Forbidden (403)
    with pytest.raises(AppError) as exc_info:
        _assert_ownership(u1_conv, caller_user_id=None)
    assert exc_info.value.code == "CONVERSATION_FORBIDDEN"

    # User 1 caller accessing anon conv -> Forbidden (403)
    with pytest.raises(AppError) as exc_info:
        _assert_ownership(anon_conv, caller_user_id="user_1")
    assert exc_info.value.code == "CONVERSATION_FORBIDDEN"
