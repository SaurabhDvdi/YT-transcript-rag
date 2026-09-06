import { config } from "../config/env";
import type {
  HealthResponse,
  VideoAnalyzeRequest,
  VideoAnalyzeResponse,
  VideoStatusResponse,
  TranscriptResponse,
  RetrievalResponse,
  AskQuestionResponse,
  CreateConversationResponse,
  ConversationListResponse,
  ConversationDetailResponse,
  ConversationMessagesResponse,
  ConversationUpdateResponse,
  ConversationDeleteResponse,
  ApiErrorResponse,
  ApiErrorCode,
} from "@youtube-ai/shared-types";
import { SSEParser, type StreamHandlers } from "./sse-parser";
import { getOrCreateSessionId } from "./session";
import { authService } from "./auth";

/**
 * Custom error thrown by the ApiClient.
 * Contains structured error code, status code, and optional server request ID.
 */
export class ApiClientError extends Error {
  public readonly code: ApiErrorCode | string;
  public readonly statusCode: number;
  public readonly requestId?: string;
  public readonly userMessage: string;

  constructor(
    message: string,
    code: ApiErrorCode | string = "INTERNAL_ERROR",
    statusCode: number = 500,
    requestId?: string,
    userMessage?: string,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.statusCode = statusCode;
    this.requestId = requestId;

    if (userMessage) {
      this.userMessage = userMessage;
    } else if (code === "QUOTA_EXCEEDED") {
      this.userMessage = "Daily usage limit reached. Quota resets at 00:00 UTC.";
    } else if (code === "CONCURRENT_STREAM_LIMIT_EXCEEDED") {
      this.userMessage =
        "Another query is currently streaming. Please wait for it to finish.";
    } else if (code === "RATE_LIMITED") {
      this.userMessage = "Too many requests. Please slow down and try again shortly.";
    } else if (code === "SERVICE_UNAVAILABLE" || code === "LLM_PROVIDER_UNAVAILABLE") {
      this.userMessage =
        "The AI service is temporarily unavailable. Please try again shortly.";
    } else {
      this.userMessage = "Unable to communicate with the YouTube AI service.";
    }
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
  retries?: number;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly defaultTimeoutMs: number;

  constructor(
    baseUrl: string = config.api.baseUrl,
    defaultTimeoutMs: number = config.api.timeoutMs,
  ) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  /**
   * Internal request executor with timeout, request ID, and safe error parsing.
   */
  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const {
      method = "GET",
      headers = {},
      body,
      signal,
      timeoutMs = this.defaultTimeoutMs,
      retries = 0,
    } = options;

    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const requestId = crypto.randomUUID();
    const sessionId = await getOrCreateSessionId();

    // Auth headers: inject Bearer token if authenticated, fall back to anonymous
    const authHeaders = await authService.getAuthHeaders();

    const requestHeaders: Record<string, string> = {
      Accept: "application/json",
      "X-Request-ID": requestId,
      "X-Session-ID": sessionId,
      ...authHeaders,
      ...headers,
    };

    if (body !== undefined) {
      requestHeaders["Content-Type"] = "application/json";
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort(new Error("Request timed out"));
    }, timeoutMs);

    // Chain caller's abort signal if supplied
    if (signal) {
      signal.addEventListener("abort", () => {
        controller.abort(signal.reason);
      });
    }

    try {
      const response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const serverRequestId = response.headers.get("X-Request-ID") || requestId;

      // Handle non-2xx responses
      if (!response.ok) {
        let errorData: ApiErrorResponse | null = null;
        try {
          errorData = (await response.json()) as ApiErrorResponse;
        } catch {
          // Response was not JSON
        }

        const errorCode = errorData?.error?.code ?? `HTTP_${response.status}`;
        const errorMessage =
          errorData?.error?.message ??
          `API request failed with status ${response.status} (${response.statusText})`;

        // Silent 401 refresh: attempt token refresh and retry once
        if (response.status === 401 && retries > 0) {
          const refreshed = await authService.refreshIfNeeded();
          if (refreshed) {
            return await this.request<T>(path, {
              ...options,
              retries: retries - 1,
            });
          }
        }

        // Safe retry for GET requests on transient 503 or server errors
        if (
          method === "GET" &&
          retries > 0 &&
          (response.status === 503 || response.status === 504)
        ) {
          return await this.request<T>(path, {
            ...options,
            retries: retries - 1,
          });
        }

        throw new ApiClientError(
          errorMessage,
          errorCode,
          response.status,
          serverRequestId,
        );
      }

      // Parse successful response
      try {
        const data = (await response.json()) as T;
        return data;
      } catch {
        throw new ApiClientError(
          "Failed to parse server response as JSON.",
          "INVALID_RESPONSE",
          response.status,
          serverRequestId,
          "Invalid response received from server.",
        );
      }
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiClientError) {
        throw error;
      }

      // Handle caller abort
      if (signal?.aborted) {
        throw new ApiClientError(
          "Request was cancelled by caller.",
          "ABORTED",
          0,
          requestId,
          "Request cancelled.",
        );
      }

      // Handle timeout
      if (controller.signal.aborted) {
        throw new ApiClientError(
          `Request timed out after ${timeoutMs}ms.`,
          "TIMEOUT_ERROR",
          0,
          requestId,
          "The server took too long to respond. Please try again.",
        );
      }

      // Handle network failure with optional safe retry on GET
      if (method === "GET" && retries > 0) {
        return await this.request<T>(path, {
          ...options,
          retries: retries - 1,
        });
      }

      throw new ApiClientError(
        error instanceof Error ? error.message : "Network error occurred.",
        "NETWORK_ERROR",
        0,
        requestId,
        "Cannot connect to the server. Please verify your backend is running.",
      );
    }
  }

  /**
   * GET /api/v1/health
   */
  public async health(signal?: AbortSignal): Promise<HealthResponse> {
    return this.request<HealthResponse>("/api/v1/health", {
      method: "GET",
      signal,
      retries: 1, // Safe to retry once on transient failure
    });
  }

  /**
   * POST /api/v1/videos
   */
  public async registerVideo(
    request: VideoAnalyzeRequest,
    signal?: AbortSignal,
  ): Promise<VideoAnalyzeResponse> {
    return this.request<VideoAnalyzeResponse>("/api/v1/videos", {
      method: "POST",
      body: request,
      signal,
      retries: 0, // Conservative: no blind retries on POST
    });
  }

  /**
   * GET /api/v1/videos/:videoId
   */
  public async getVideoStatus(
    videoId: string,
    signal?: AbortSignal,
  ): Promise<VideoStatusResponse> {
    return this.request<VideoStatusResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}`,
      {
        method: "GET",
        signal,
        retries: 1,
      },
    );
  }

  /**
   * GET /api/v1/videos/:videoId/transcript
   */
  public async getTranscript(
    videoId: string,
    signal?: AbortSignal,
  ): Promise<TranscriptResponse> {
    return this.request<TranscriptResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}/transcript`,
      {
        method: "GET",
        signal,
        retries: 0,
      },
    );
  }

  /**
   * POST /api/v1/videos/:videoId/retrieval
   * Searches the semantic retrieval index for timestamped chunks.
   */
  public async searchRetrieval(
    videoId: string,
    query: string,
    topK?: number,
    signal?: AbortSignal,
  ): Promise<RetrievalResponse> {
    return this.request<RetrievalResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}/retrieval`,
      {
        method: "POST",
        body: { query, ...(topK !== undefined ? { topK } : {}) },
        signal,
        retries: 0,
      },
    );
  }

  /**
   * POST /api/v1/videos/:videoId/ask
   * Generates a grounded, timestamp-cited answer to a user question using transcript evidence.
   */
  public async askQuestion(
    videoId: string,
    question: string,
    options?: {
      topK?: number;
      conversationId?: string;
      clientRequestId?: string;
    },
    signal?: AbortSignal,
  ): Promise<AskQuestionResponse> {
    return this.request<AskQuestionResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}/ask`,
      {
        method: "POST",
        body: {
          question,
          ...(options?.topK !== undefined ? { topK: options.topK } : {}),
          ...(options?.conversationId ? { conversationId: options.conversationId } : {}),
          ...(options?.clientRequestId
            ? { clientRequestId: options.clientRequestId }
            : {}),
        },
        signal,
        retries: 0,
      },
    );
  }

  /**
   * POST /api/v1/videos/:videoId/conversations
   */
  public async createConversation(
    videoId: string,
    signal?: AbortSignal,
  ): Promise<CreateConversationResponse> {
    return this.request<CreateConversationResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}/conversations`,
      {
        method: "POST",
        signal,
        retries: 0,
      },
    );
  }

  /**
   * GET /api/v1/videos/:videoId/conversations
   */
  public async listConversations(
    videoId: string,
    limit?: number,
    signal?: AbortSignal,
  ): Promise<ConversationListResponse> {
    const query = limit ? `?limit=${encodeURIComponent(limit)}` : "";
    return this.request<ConversationListResponse>(
      `/api/v1/videos/${encodeURIComponent(videoId)}/conversations${query}`,
      {
        method: "GET",
        signal,
        retries: 0,
      },
    );
  }

  /**
   * GET /api/v1/conversations/:conversationId
   */
  public async getConversation(
    conversationId: string,
    signal?: AbortSignal,
  ): Promise<ConversationDetailResponse> {
    return this.request<ConversationDetailResponse>(
      `/api/v1/conversations/${encodeURIComponent(conversationId)}`,
      {
        method: "GET",
        signal,
        retries: 0,
      },
    );
  }

  /**
   * GET /api/v1/conversations/:conversationId/messages
   */
  public async getConversationMessages(
    conversationId: string,
    limit?: number,
    cursor?: string,
    signal?: AbortSignal,
  ): Promise<ConversationMessagesResponse> {
    const params = new URLSearchParams();
    if (limit) params.set("limit", limit.toString());
    if (cursor) params.set("cursor", cursor);
    const qs = params.toString() ? `?${params.toString()}` : "";

    return this.request<ConversationMessagesResponse>(
      `/api/v1/conversations/${encodeURIComponent(conversationId)}/messages${qs}`,
      {
        method: "GET",
        signal,
        retries: 0,
      },
    );
  }

  /**
   * Streams grounded question answering over SSE.
   */
  public async streamQuestion(
    videoId: string,
    question: string,
    options: {
      conversationId?: string;
      clientRequestId?: string;
      topK?: number;
    } = {},
    handlers: StreamHandlers,
    signal?: AbortSignal,
  ): Promise<void> {
    const url = `${this.baseUrl}/api/v1/videos/${encodeURIComponent(videoId)}/ask?stream=true`;
    const requestId = options.clientRequestId ?? crypto.randomUUID();
    const sessionId = await getOrCreateSessionId();

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "X-Request-ID": requestId,
        "X-Session-ID": sessionId,
      },
      body: JSON.stringify({
        question,
        conversationId: options.conversationId,
        clientRequestId: options.clientRequestId,
        topK: options.topK,
      }),
      signal,
    });

    if (!response.ok) {
      let errCode = "INTERNAL_ERROR";
      let errMsg = `Request failed with status ${response.status}`;
      try {
        const errJson = (await response.json()) as ApiErrorResponse;
        if (errJson.error) {
          errCode = errJson.error.code;
          errMsg = errJson.error.message;
        }
      } catch {
        // fallback
      }
      const err = new ApiClientError(errMsg, errCode, response.status, requestId);
      handlers.onError?.({
        type: "error",
        code: errCode,
        message: err.userMessage || errMsg,
      });
      throw err;
    }

    if (!response.body) {
      throw new ApiClientError("No response body stream", "STREAM_INTERRUPTED", 500);
    }

    const parser = new SSEParser(handlers);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        if (signal?.aborted) {
          await reader.cancel();
          handlers.onError?.({
            type: "error",
            code: "STREAM_ABORTED",
            message: "Request aborted by user",
          });
          return;
        }

        const { done, value } = await reader.read();
        if (done) break;
        if (value) {
          parser.feed(decoder.decode(value, { stream: true }));
        }
      }
      parser.flush();
    } catch (err: unknown) {
      if (signal?.aborted) return;
      const msg = err instanceof Error ? err.message : "Stream read error";
      handlers.onError?.({
        type: "error",
        code: "STREAM_INTERRUPTED",
        message: msg,
      });
      throw err;
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * PATCH /api/v1/conversations/:conversationId
   */
  public async updateConversationTitle(
    conversationId: string,
    title: string,
    videoId?: string,
    signal?: AbortSignal,
  ): Promise<ConversationUpdateResponse> {
    const qs = videoId ? `?videoId=${encodeURIComponent(videoId)}` : "";
    return this.request<ConversationUpdateResponse>(
      `/api/v1/conversations/${encodeURIComponent(conversationId)}${qs}`,
      {
        method: "PATCH",
        body: { title, videoId },
        signal,
        retries: 0,
      },
    );
  }

  /**
   * DELETE /api/v1/conversations/:conversationId
   */
  public async deleteConversation(
    conversationId: string,
    videoId?: string,
    signal?: AbortSignal,
  ): Promise<ConversationDeleteResponse> {
    const qs = videoId ? `?videoId=${encodeURIComponent(videoId)}` : "";
    return this.request<ConversationDeleteResponse>(
      `/api/v1/conversations/${encodeURIComponent(conversationId)}${qs}`,
      {
        method: "DELETE",
        signal,
        retries: 0,
      },
    );
  }
}

// Singleton default client
export const apiClient = new ApiClient();
