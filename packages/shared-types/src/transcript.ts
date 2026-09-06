import type { Transcript } from "./video";

/**
 * Categorized error codes for transcript acquisition and normalization failures.
 */
export type TranscriptErrorCode =
  | "TRANSCRIPT_NOT_FOUND"
  | "CAPTIONS_UNAVAILABLE"
  | "VIDEO_UNAVAILABLE"
  | "LANGUAGE_UNAVAILABLE"
  | "PROVIDER_TEMPORARY_FAILURE"
  | "PROVIDER_INVALID_RESPONSE"
  | "TRANSCRIPT_TOO_LARGE"
  | "UNSUPPORTED_VIDEO"
  | "TRANSCRIPT_NOT_READY";

/**
 * Successful response returned by GET /api/v1/videos/:videoId/transcript.
 */
export interface TranscriptResponse {
  success: true;
  videoId: string;
  transcript: Transcript;
  requestId: string;
}
