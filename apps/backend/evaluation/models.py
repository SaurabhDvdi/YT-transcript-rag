"""Pydantic schemas and dataclasses for Phase 12 Evaluation Framework."""

from typing import Any

from pydantic import BaseModel, Field


class EvidenceInterval(BaseModel):
    start: float
    end: float
    keyPhrase: str | None = None


class VideoBenchmarkItem(BaseModel):
    videoId: str
    title: str
    category: str
    durationSeconds: int
    durationTier: str
    speechDensity: str
    speakerCount: int
    hasSpeakerLabels: bool
    language: str
    inclusionRationale: str


class RetrievalTestCase(BaseModel):
    id: str
    videoId: str
    question: str
    questionType: str
    category: str
    expectedEvidence: list[EvidenceInterval] = Field(default_factory=list)
    expectedChunkIds: list[str] = Field(default_factory=list)


class QARubric(BaseModel):
    correctness: str
    groundedness: str
    relevance: str


class QATestCase(BaseModel):
    id: str
    retrievalId: str
    videoId: str
    question: str
    questionType: str
    referenceAnswer: str
    keyFacts: list[str] = Field(default_factory=list)
    isNoEvidence: bool = False
    rubric: QARubric


class CitationTestCase(BaseModel):
    id: str
    qaId: str
    videoId: str
    textWithMarkers: str
    evidenceChunks: list[dict[str, Any]] = Field(default_factory=list)
    expectedValidMarkers: list[str] = Field(default_factory=list)
    expectedPhantomMarkers: list[str] = Field(default_factory=list)
    goldTimestampIntervals: list[dict[str, float]] = Field(default_factory=list)


class ConversationalTestCase(BaseModel):
    id: str
    videoId: str
    history: list[dict[str, str]] = Field(default_factory=list)
    currentQuestion: str
    isSelfContained: bool = False
    expectedSubject: str
    expectedRewrittenQuery: str


class AdversarialTestCase(BaseModel):
    id: str
    attackType: str
    payload: Any
    expectedSafetyOutcome: str
    description: str


# ---------------------------------------------------------------------------
# Evaluation Output Metrics Models
# ---------------------------------------------------------------------------


class RetrievalMetrics(BaseModel):
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    precision_at_5: float
    mrr: float
    mean_iou: float
    category_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    question_type_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    duration_tier_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)


class RewritingMetrics(BaseModel):
    rewrite_accuracy: float
    entity_preservation_rate: float
    topic_preservation_rate: float
    no_rewrite_preservation_rate: float
    total_cases: int


class ContextMetrics(BaseModel):
    context_precision: float
    context_recall: float
    duplicate_chunk_rate: float
    unique_evidence_coverage: float


class GenerationMetrics(BaseModel):
    grounded_answer_rate: float
    unsupported_claim_rate: float
    hallucination_rate: float
    correct_abstention_rate: float
    no_answer_precision: float
    no_answer_recall: float
    answer_correctness_score: float  # 0.0 - 1.0 (or 1.0 - 5.0 scaled)
    category_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)


class CitationMetrics(BaseModel):
    citation_precision: float
    citation_recall: float
    citation_validity_rate: float
    mean_temporal_iou: float
    phantom_rejection_rate: float


class LatencyPercentiles(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float


class ComponentLatencyBreakdown(BaseModel):
    retrieval_ms: LatencyPercentiles
    llm_ttft_ms: LatencyPercentiles
    llm_total_ms: LatencyPercentiles
    citation_resolution_ms: LatencyPercentiles
    end_to_end_ms: LatencyPercentiles


class SecurityMetrics(BaseModel):
    transcript_injection_defense_rate: float
    user_prompt_injection_defense_rate: float
    conversation_injection_defense_rate: float
    cross_video_isolation_rate: float
    cross_user_isolation_rate: float
    overall_safety_rate: float


class EvaluationTrace(BaseModel):
    test_id: str
    video_id: str
    question: str
    rewritten_query: str | None = None
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    retrieval_scores: list[float] = Field(default_factory=list)
    context_passed_to_model: str = ""
    model_raw_answer: str = ""
    resolved_citations: list[dict[str, Any]] = Field(default_factory=list)
    is_grounded: bool = False
    status: str = "PASS"
    error_stage: str | None = None
    error_taxonomy: str | None = None


class BenchmarkMetadata(BaseModel):
    dataset_version: str = "v1.0.0"
    code_version: str = "0.1.0"
    prompt_version: str = "v1.0"
    embedding_provider: str = "deterministic-384d"
    chunker_version: str = "semantic-sliding-window-v1"
    llm_provider: str = "mock-llm"
    llm_model: str = "mock-model-v1"
    run_timestamp: str
    environment: str = "evaluation-offline"


class EvaluationReportSummary(BaseModel):
    metadata: BenchmarkMetadata
    retrieval: RetrievalMetrics
    rewriting: RewritingMetrics
    context: ContextMetrics
    generation: GenerationMetrics
    citations: CitationMetrics
    latency: ComponentLatencyBreakdown
    security: SecurityMetrics
    regression_gate_status: str  # "PASS" | "FAIL"
    traces: list[EvaluationTrace] = Field(default_factory=list)
