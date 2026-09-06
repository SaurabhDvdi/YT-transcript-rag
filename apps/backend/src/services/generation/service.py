"""Generation service orchestrating grounded Q&A, query rewriting, citations, and streaming."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from src.core.constants import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_QUESTION_LENGTH,
    NO_EVIDENCE_ANSWER_TEXT,
)
from src.core.errors import AppError
from src.schemas.conversation import ConversationMessage
from src.schemas.generation import (
    CitationStreamEvent,
    DoneStreamEvent,
    ErrorStreamEvent,
    StartStreamEvent,
    StreamEvent,
    TokenStreamEvent,
)
from src.services.conversation.service import ConversationService
from src.services.conversation.title_generator import generate_title_from_query
from src.services.generation.citation_resolver import CitationResolver
from src.services.generation.constants import MAX_STREAMED_OUTPUT_CHARS
from src.services.generation.context_builder import ContextBuilder
from src.services.generation.prompts.grounded_qa import (
    build_grounded_qa_system_prompt,
    build_grounded_qa_user_prompt,
    format_conversation_history,
)
from src.services.generation.providers.mock import MockLLMProvider
from src.services.generation.rewriter.deterministic import DeterministicQueryRewriter
from src.services.generation.rewriter.types import QueryRewriter
from src.services.generation.router import LLMRouter
from src.services.generation.types import (
    GenerationOptions,
    GenerationResult,
    LLMGenerationRequest,
)
from src.services.retrieval.service import RetrievalService


class GenerationService:
    """Orchestrator service for grounded question answering over transcript evidence.
    Integrates retrieval, context budgeting, grounding prompts, provider routing,
    multi-turn conversation persistence, query rewriting, streaming, and citation resolution.
    """

    _instance: "GenerationService | None" = None

    def __init__(
        self,
        router: LLMRouter | None = None,
        retrieval_service: RetrievalService | None = None,
        context_builder: ContextBuilder | None = None,
        citation_resolver: CitationResolver | None = None,
        conversation_service: ConversationService | None = None,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self.router: LLMRouter = router or LLMRouter(MockLLMProvider())
        self.retrieval_service: RetrievalService = (
            retrieval_service or RetrievalService.get_instance()
        )
        self.context_builder: ContextBuilder = context_builder or ContextBuilder()
        self.citation_resolver: CitationResolver = citation_resolver or CitationResolver()
        self.conversation_service: ConversationService = (
            conversation_service or ConversationService.get_instance()
        )
        self.query_rewriter: QueryRewriter = query_rewriter or DeterministicQueryRewriter()

    @classmethod
    def get_instance(cls) -> "GenerationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "GenerationService | None") -> None:
        cls._instance = instance

    def get_router(self) -> LLMRouter:
        return self.router

    def get_retrieval_service(self) -> RetrievalService:
        return self.retrieval_service

    async def answer_question(
        self,
        video_id: str,
        question: str,
        options: GenerationOptions | None = None,
    ) -> GenerationResult:
        """Answers a user question strictly grounded in the video's transcript evidence."""
        trimmed = question.strip()
        if not trimmed:
            raise AppError("INVALID_QUESTION", 400, "Question must not be empty")

        if len(trimmed) > MAX_QUESTION_LENGTH:
            raise AppError(
                "INVALID_QUESTION",
                400,
                f"Question exceeds maximum allowed length of {MAX_QUESTION_LENGTH} characters",
            )

        conversation_id = options.conversation_id if options else None
        client_request_id = options.client_request_id if options else None
        history: list[ConversationMessage] = []

        if conversation_id:
            # 1. Verify conversation exists and belongs to the video
            await self.conversation_service.validate_conversation_for_video(
                conversation_id, video_id
            )

            # 2. Idempotency guard
            if client_request_id:
                existing_msg = await self.conversation_service.get_message_by_client_request_id(
                    client_request_id
                )
                if existing_msg:
                    recent = await self.conversation_service.get_recent_messages(
                        conversation_id, 20
                    )
                    try:
                        user_idx = next(i for i, m in enumerate(recent) if m.id == existing_msg.id)
                        if user_idx < len(recent) - 1:
                            next_msg = recent[user_idx + 1]
                            if next_msg.role == "assistant":
                                return GenerationResult(
                                    text=next_msg.content,
                                    grounded=next_msg.grounded
                                    if next_msg.grounded is not None
                                    else True,
                                    citations=next_msg.citations or [],
                                    message_id=next_msg.id,
                                )
                    except StopIteration:
                        pass

            # 3. Load bounded recent history before adding the new user message
            history = await self.conversation_service.get_recent_messages(conversation_id, 10)

            # 4. Persist user message
            await self.conversation_service.add_user_message(
                conversation_id,
                trimmed,
                client_request_id,
            )

        # 5. Query Rewriting: derive self-contained retrieval query if conversational follow-up
        retrieval_query = trimmed
        if history:
            retrieval_query = await self.query_rewriter.rewrite(trimmed, history)

        # 6. Retrieve top-K evidence chunks strictly for the current video
        top_k = options.top_k if options else 5
        search_results = await self.retrieval_service.search(video_id, retrieval_query, top_k)

        # 7. Build bounded evidence context
        context = self.context_builder.build_context(search_results)

        # 8. Zero-evidence guard: return immediately without spending LLM quota
        if not context.has_evidence:
            saved_msg_id: str | None = None
            if conversation_id:
                assistant_msg = await self.conversation_service.add_assistant_message(
                    conversation_id,
                    NO_EVIDENCE_ANSWER_TEXT,
                    [],
                    False,
                )
                saved_msg_id = assistant_msg.id

                if not history:
                    conv = await self.conversation_service.get_conversation(conversation_id)
                    if conv and conv.title_source == "auto":
                        gen_title = generate_title_from_query(trimmed)
                        await self.conversation_service.update_conversation_title(
                            conversation_id, gen_title, "auto"
                        )

            return GenerationResult(
                text=NO_EVIDENCE_ANSWER_TEXT,
                grounded=False,
                citations=[],
                message_id=saved_msg_id,
            )

        # 9. Construct prompts with separate evidence and history sections
        system_prompt = build_grounded_qa_system_prompt()
        formatted_history = format_conversation_history(history) if history else None
        user_prompt = build_grounded_qa_user_prompt(
            trimmed, context.formatted_context, formatted_history
        )

        # 10. Execute generation via provider router
        timeout_ms = options.timeout_ms if options else None
        generation_resp = await self.router.generate(
            LLMGenerationRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
            ),
            timeout_ms=timeout_ms,
        )

        # 11. Validate output
        raw_answer_text = generation_resp.text.strip()
        if not raw_answer_text:
            raise AppError("LLM_OUTPUT_INVALID", 502, "LLM provider returned empty text")

        # 12. Resolve citations and strip phantom markers
        resolved = self.citation_resolver.resolve_citations(
            raw_answer_text, context.evidence_chunks
        )

        assistant_msg_id: str | None = None
        if conversation_id:
            assistant_msg = await self.conversation_service.add_assistant_message(
                conversation_id,
                resolved.cleaned_text,
                resolved.citations,
                resolved.grounded,
            )
            assistant_msg_id = assistant_msg.id

            # 13. Auto-title generation after first assistant response
            if not history:
                conv = await self.conversation_service.get_conversation(conversation_id)
                if conv and conv.title_source == "auto":
                    gen_title = generate_title_from_query(trimmed)
                    await self.conversation_service.update_conversation_title(
                        conversation_id, gen_title, "auto"
                    )

        return GenerationResult(
            text=resolved.cleaned_text,
            grounded=resolved.grounded,
            citations=resolved.citations,
            message_id=assistant_msg_id,
        )

    async def stream_answer_question(
        self,
        video_id: str,
        question: str,
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Streams a grounded answer to a user question using SSE StreamEvents.
        Atomically persists messages and citations only upon successful finalization.
        """
        trimmed = question.strip()
        if not trimmed:
            raise AppError("INVALID_QUESTION", 400, "Question must not be empty")

        if len(trimmed) > MAX_QUESTION_LENGTH:
            raise AppError(
                "INVALID_QUESTION",
                400,
                f"Question exceeds maximum allowed length of ${MAX_QUESTION_LENGTH} characters",
            )

        conversation_id = options.conversation_id if options else None
        client_request_id = options.client_request_id if options else None
        history: list[ConversationMessage] = []

        if conversation_id:
            await self.conversation_service.validate_conversation_for_video(
                conversation_id, video_id
            )

            # Idempotency check
            if client_request_id:
                existing_msg = await self.conversation_service.get_message_by_client_request_id(
                    client_request_id
                )
                if existing_msg:
                    recent = await self.conversation_service.get_recent_messages(
                        conversation_id, 20
                    )
                    try:
                        user_idx = next(i for i, m in enumerate(recent) if m.id == existing_msg.id)
                        if user_idx < len(recent) - 1:
                            next_msg = recent[user_idx + 1]
                            if next_msg.role == "assistant":
                                yield StartStreamEvent(
                                    request_id=client_request_id,
                                    conversation_id=conversation_id,
                                    message_id=next_msg.id,
                                )
                                yield TokenStreamEvent(text=next_msg.content)
                                if next_msg.citations:
                                    for cite in next_msg.citations:
                                        yield CitationStreamEvent(citation=cite)
                                yield DoneStreamEvent(message=next_msg)
                                return
                    except StopIteration:
                        pass

            history = await self.conversation_service.get_recent_messages(conversation_id, 10)

        retrieval_query = trimmed
        if history:
            retrieval_query = await self.query_rewriter.rewrite(trimmed, history)

        top_k = options.top_k if options else 5
        search_results = await self.retrieval_service.search(video_id, retrieval_query, top_k)
        context = self.context_builder.build_context(search_results)

        request_id = client_request_id or str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())

        # Zero-evidence case
        if not context.has_evidence:
            yield StartStreamEvent(
                request_id=request_id,
                conversation_id=conversation_id or "",
                message_id=assistant_message_id,
            )
            yield TokenStreamEvent(text=NO_EVIDENCE_ANSWER_TEXT)

            finalized_message = ConversationMessage(
                id=assistant_message_id,
                conversation_id=conversation_id or "",
                role="assistant",
                content=NO_EVIDENCE_ANSWER_TEXT,
                citations=[],
                grounded=False,
                created_at=datetime.now(UTC).isoformat(),
            )

            if conversation_id:
                await self.conversation_service.add_user_message(
                    conversation_id, trimmed, client_request_id
                )
                saved_msg = await self.conversation_service.add_assistant_message(
                    conversation_id,
                    NO_EVIDENCE_ANSWER_TEXT,
                    [],
                    False,
                )
                finalized_message = saved_msg

                if not history:
                    conv = await self.conversation_service.get_conversation(conversation_id)
                    if conv and conv.title_source == "auto":
                        gen_title = generate_title_from_query(trimmed)
                        await self.conversation_service.update_conversation_title(
                            conversation_id, gen_title, "auto"
                        )

            yield DoneStreamEvent(message=finalized_message)
            return

        # Start streaming response
        yield StartStreamEvent(
            request_id=request_id,
            conversation_id=conversation_id or "",
            message_id=assistant_message_id,
        )

        system_prompt = build_grounded_qa_system_prompt()
        formatted_history = format_conversation_history(history) if history else None
        user_prompt = build_grounded_qa_user_prompt(
            trimmed, context.formatted_context, formatted_history
        )

        timeout_ms = options.timeout_ms if options else None
        accumulated_text = ""

        try:
            async for chunk in self.router.stream(
                LLMGenerationRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                    temperature=DEFAULT_TEMPERATURE,
                ),
                timeout_ms=timeout_ms,
            ):
                if chunk.text:
                    accumulated_text += chunk.text
                    yield TokenStreamEvent(text=chunk.text)
                    if len(accumulated_text) >= MAX_STREAMED_OUTPUT_CHARS:
                        break

            raw_answer = accumulated_text.strip()
            if not raw_answer:
                yield ErrorStreamEvent(
                    code="LLM_OUTPUT_INVALID",
                    message="LLM provider returned empty text",
                )
                return

            resolved = self.citation_resolver.resolve_citations(raw_answer, context.evidence_chunks)

            for cite in resolved.citations:
                yield CitationStreamEvent(citation=cite)

            saved_message = ConversationMessage(
                id=assistant_message_id,
                conversation_id=conversation_id or "",
                role="assistant",
                content=resolved.cleaned_text,
                citations=resolved.citations,
                grounded=resolved.grounded,
                created_at=datetime.now(UTC).isoformat(),
            )

            if conversation_id:
                await self.conversation_service.add_user_message(
                    conversation_id, trimmed, client_request_id
                )
                persisted_assistant = await self.conversation_service.add_assistant_message(
                    conversation_id,
                    resolved.cleaned_text,
                    resolved.citations,
                    resolved.grounded,
                )
                saved_message = persisted_assistant

                if not history:
                    conv = await self.conversation_service.get_conversation(conversation_id)
                    if conv and conv.title_source == "auto":
                        gen_title = generate_title_from_query(trimmed)
                        await self.conversation_service.update_conversation_title(
                            conversation_id, gen_title, "auto"
                        )

            yield DoneStreamEvent(message=saved_message)

        except AppError as ae:
            yield ErrorStreamEvent(code=ae.code, message=ae.message)
        except Exception as e:
            yield ErrorStreamEvent(
                code="STREAM_INTERRUPTED",
                message=str(e) or "Streaming generation failed",
            )
