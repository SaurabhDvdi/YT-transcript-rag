/**
 * Standardized API error codes used across the backend and client.
 */
export type ApiErrorCode =
  | "INVALID_REQUEST"
  | "INVALID_VIDEO_ID"
  | "METHOD_NOT_ALLOWED"
  | "NOT_FOUND"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "RETRIEVAL_NOT_READY"
  | "INVALID_QUERY"
  | "INVALID_TOP_K"
  | "INVALID_QUESTION"
  | "GENERATION_FAILED"
  | "LLM_PROVIDER_UNAVAILABLE"
  | "LLM_TIMEOUT"
  | "LLM_OUTPUT_INVALID"
  | "CONVERSATION_NOT_FOUND"
  | "CONVERSATION_VIDEO_MISMATCH"
  | "INVALID_CONVERSATION_ID"
  | "DUPLICATE_REQUEST"
  | "MESSAGE_LIMIT_EXCEEDED"
  | "STREAM_INTERRUPTED"
  | "STREAM_TIMEOUT"
  | "STREAM_ABORTED"
  | "QUOTA_EXCEEDED"
  | "CONCURRENT_STREAM_LIMIT_EXCEEDED"
  | "JOB_FAILED"
  | "JOB_NOT_FOUND";

/**
 * Structured error details payload.
 */
export interface ApiErrorDetail {
  code: ApiErrorCode | string;
  message: string;
}

/**
 * Standard error response envelope returned by all backend endpoints.
 */
export interface ApiErrorResponse {
  success: false;
  error: ApiErrorDetail;
  requestId: string;
}
