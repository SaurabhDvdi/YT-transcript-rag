/**
 * A resolved citation traceable to an exact transcript chunk and timestamp boundary.
 */
export interface Citation {
  chunkId: string;
  start: number;
  end: number;
  score?: number;
}

/**
 * Structured answer returned by the grounded generation engine.
 */
export interface GroundedAnswer {
  text: string;
  grounded: boolean;
  citations: Citation[];
}

/**
 * Request payload to ask a question about a video's transcript.
 */
export interface AskQuestionRequest {
  question: string;
  conversationId?: string;
  clientRequestId?: string;
  topK?: number;
}

/**
 * Response envelope returned upon successful question answering.
 */
export interface AskQuestionResponse {
  success: true;
  videoId: string;
  conversationId?: string;
  answer: GroundedAnswer;
  message?: {
    id: string;
    role: "assistant";
    text: string;
    grounded: boolean;
    citations: Citation[];
    createdAt?: string;
  };
  requestId: string;
}

/**
 * Domain error codes specific to grounded answer generation.
 */
export type GenerationErrorCode =
  | "INVALID_QUESTION"
  | "GENERATION_FAILED"
  | "LLM_PROVIDER_UNAVAILABLE"
  | "LLM_TIMEOUT"
  | "LLM_OUTPUT_INVALID";
