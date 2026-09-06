/**
 * Status lifecycle states for video retrieval indexing.
 */
export type RetrievalStatus = "not_ready" | "indexing" | "ready" | "error";

/**
 * A normalized, timestamped retrieval chunk traceable to the original transcript segments.
 * Preserves timing boundaries for citation seeking and downstream LLM grounding.
 */
export interface RetrievalChunk {
  id: string;
  videoId: string;
  chunkIndex: number;
  text: string;
  start: number;
  end: number;
  segmentStartIndex: number;
  segmentEndIndex: number;
  tokenCount: number;
}

/**
 * Scored search result returned by the retriever.
 */
export interface RetrievalResult {
  chunk: RetrievalChunk;
  score: number;
}

/**
 * Request payload to query the video retrieval index.
 */
export interface RetrievalRequest {
  query: string;
  topK?: number;
}

/**
 * Response payload returned upon successful retrieval search.
 */
export interface RetrievalResponse {
  success: true;
  videoId: string;
  results: RetrievalResult[];
  requestId: string;
}

/**
 * Domain error codes specific to retrieval operations.
 */
export type RetrievalErrorCode =
  "RETRIEVAL_NOT_READY" | "INVALID_QUERY" | "INVALID_TOP_K";
