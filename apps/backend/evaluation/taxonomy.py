"""Error taxonomy classification and root-cause analysis for Phase 12 Evaluation."""

from dataclasses import dataclass
from enum import StrEnum


class ErrorCategory(StrEnum):
    TRANSCRIPT_ERROR = "TRANSCRIPT_ERROR"
    CHUNKING_ERROR = "CHUNKING_ERROR"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RETRIEVAL_IRRELEVANCE = "RETRIEVAL_IRRELEVANCE"
    QUERY_REWRITE_ERROR = "QUERY_REWRITE_ERROR"
    CONTEXT_SELECTION_ERROR = "CONTEXT_SELECTION_ERROR"
    GENERATION_ERROR = "GENERATION_ERROR"
    HALLUCINATION = "HALLUCINATION"
    CITATION_ERROR = "CITATION_ERROR"
    PERSISTENCE_ERROR = "PERSISTENCE_ERROR"
    UI_ERROR = "UI_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"


@dataclass
class RootCauseDiagnostic:
    stage: str
    error_category: ErrorCategory
    description: str
    remedy_hint: str


class FailureDiagnoser:
    """Diagnoses evaluation failures across the pipeline stages:
    question -> query_rewrite -> retrieval -> context_selection -> generation -> citation_resolution
    Identifies the earliest stage where correctness was lost.
    """

    @staticmethod
    def diagnose_stage(
        has_retrieval_evidence: bool,
        gold_evidence_present: bool,
        is_rewritten: bool,
        rewrite_preserved_intent: bool,
        context_has_gold: bool,
        generation_answered: bool,
        is_no_evidence_expected: bool,
        has_hallucination: bool,
        citations_valid: bool,
    ) -> RootCauseDiagnostic:
        # Stage 1: Query rewriting
        if is_rewritten and not rewrite_preserved_intent:
            return RootCauseDiagnostic(
                stage="query_rewriter",
                error_category=ErrorCategory.QUERY_REWRITE_ERROR,
                description="Query rewriter distorted user intent, introduced incorrect subject, or corrupted self-contained query.",
                remedy_hint="Adjust pronoun resolution patterns or stop-word filters in DeterministicQueryRewriter.",
            )

        # Stage 2: Retrieval
        if gold_evidence_present and not has_retrieval_evidence:
            return RootCauseDiagnostic(
                stage="retrieval",
                error_category=ErrorCategory.RETRIEVAL_MISS,
                description="Gold evidence chunk was not returned in top-K vector search results.",
                remedy_hint="Examine embedding model semantic matching or increase top-K retrieval budget.",
            )

        # Stage 3: Context Selection
        if gold_evidence_present and has_retrieval_evidence and not context_has_gold:
            return RootCauseDiagnostic(
                stage="context_builder",
                error_category=ErrorCategory.CONTEXT_SELECTION_ERROR,
                description="Retrieval returned evidence but context builder filtered it out due to similarity threshold or character budget.",
                remedy_hint="Inspect MIN_SIMILARITY_THRESHOLD (0.25) or MAX_CONTEXT_CHARACTERS budgeting in ContextBuilder.",
            )

        # Stage 4: Generation / Abstention
        if is_no_evidence_expected and generation_answered and has_hallucination:
            return RootCauseDiagnostic(
                stage="generation",
                error_category=ErrorCategory.HALLUCINATION,
                description="Model fabricated an answer when the video lacked evidence instead of cleanly abstaining.",
                remedy_hint="Strengthen grounded prompt negative constraints and verify context.has_evidence checks.",
            )

        if not is_no_evidence_expected and not generation_answered and gold_evidence_present:
            return RootCauseDiagnostic(
                stage="generation",
                error_category=ErrorCategory.GENERATION_ERROR,
                description="Model abstained or returned empty answer despite valid evidence provided in context.",
                remedy_hint="Check system prompt formatting or LLM generation parameters.",
            )

        # Stage 5: Citations
        if not citations_valid:
            return RootCauseDiagnostic(
                stage="citation_resolver",
                error_category=ErrorCategory.CITATION_ERROR,
                description="Citation markers were missing, unmapped, pointing to incorrect timestamp ranges, or phantom markers were retained.",
                remedy_hint="Verify CitationResolver regex parsing and chunk index mapping logic.",
            )

        # Default fallback
        return RootCauseDiagnostic(
            stage="pipeline",
            error_category=ErrorCategory.GENERATION_ERROR,
            description="General output discrepancy against reference expectations.",
            remedy_hint="Inspect evaluation trace for step-by-step state inspection.",
        )
