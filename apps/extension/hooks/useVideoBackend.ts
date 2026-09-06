import { useState, useEffect, useRef, useCallback } from "react";
import type { CurrentVideo } from "../types/youtube";
import type {
  TranscriptSummary,
  VideoProcessingStatus,
  RetrievalStatus,
} from "@youtube-ai/shared-types";
import { apiClient, ApiClientError } from "../services/api";

export type VideoBackendState =
  | { status: "idle" }
  | { status: "registering"; videoId: string }
  | {
      status: "connected";
      videoId: string;
      processingStatus: VideoProcessingStatus;
      transcript?: TranscriptSummary;
      retrievalStatus?: RetrievalStatus;
      requestId: string;
    }
  | {
      status: "error";
      videoId: string;
      message: string;
      code?: string;
      requestId?: string;
    };

const MAX_POLL_DURATION_MS = 45_000;
const INITIAL_POLL_INTERVAL_MS = 1_500;
const MAX_POLL_INTERVAL_MS = 5_000;
const POLL_BACKOFF_FACTOR = 1.3;

export function useVideoBackend(currentVideo: CurrentVideo | null) {
  const [backendState, setBackendState] = useState<VideoBackendState>({
    status: "idle",
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearPendingTimers = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const registerCurrentVideo = useCallback(
    async (video: CurrentVideo) => {
      // 1. Abort previous operations and timers
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      clearPendingTimers();

      const controller = new AbortController();
      abortControllerRef.current = controller;
      const targetVideoId = video.videoId;

      setBackendState({
        status: "registering",
        videoId: targetVideoId,
      });

      try {
        const response = await apiClient.registerVideo(
          { videoId: targetVideoId },
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        const initialStatus = response.video.status;
        const initialRetrievalStatus = response.retrievalStatus;
        setBackendState({
          status: "connected",
          videoId: targetVideoId,
          processingStatus: initialStatus,
          transcript: response.transcript,
          retrievalStatus: initialRetrievalStatus,
          requestId: response.requestId,
        });

        // If not terminal, initiate bounded polling
        const isTerminal =
          initialStatus === "unavailable" ||
          initialStatus === "error" ||
          (initialStatus === "ready" && initialRetrievalStatus !== "indexing");

        if (!isTerminal) {
          const startTime = Date.now();
          let currentInterval = INITIAL_POLL_INTERVAL_MS;

          const poll = async () => {
            if (controller.signal.aborted) return;

            // Check max polling duration
            if (Date.now() - startTime >= MAX_POLL_DURATION_MS) {
              return;
            }

            try {
              const statusResponse = await apiClient.getVideoStatus(
                targetVideoId,
                controller.signal,
              );

              if (controller.signal.aborted) return;

              const latestStatus = statusResponse.video.status;
              const latestRetrievalStatus = statusResponse.retrievalStatus;
              setBackendState({
                status: "connected",
                videoId: targetVideoId,
                processingStatus: latestStatus,
                transcript: statusResponse.transcript,
                retrievalStatus: latestRetrievalStatus,
                requestId: statusResponse.requestId,
              });

              if (
                latestStatus === "unavailable" ||
                latestStatus === "error" ||
                (latestStatus === "ready" && latestRetrievalStatus !== "indexing")
              ) {
                // Stop polling immediately on terminal state
                return;
              }

              // Schedule next poll with gentle exponential backoff
              currentInterval = Math.min(
                currentInterval * POLL_BACKOFF_FACTOR,
                MAX_POLL_INTERVAL_MS,
              );

              pollTimerRef.current = setTimeout(poll, currentInterval);
            } catch (pollErr) {
              if (controller.signal.aborted) return;

              // If poll fails with network/server error, stop polling and show error
              if (pollErr instanceof ApiClientError) {
                setBackendState({
                  status: "error",
                  videoId: targetVideoId,
                  message: pollErr.userMessage,
                  code: pollErr.code,
                  requestId: pollErr.requestId,
                });
              }
            }
          };

          pollTimerRef.current = setTimeout(poll, currentInterval);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiClientError) {
          setBackendState({
            status: "error",
            videoId: targetVideoId,
            message: error.userMessage,
            code: error.code,
            requestId: error.requestId,
          });
        } else {
          setBackendState({
            status: "error",
            videoId: targetVideoId,
            message:
              error instanceof Error ? error.message : "Unable to connect to backend.",
          });
        }
      }
    },
    [clearPendingTimers],
  );

  useEffect(() => {
    if (!currentVideo) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      clearPendingTimers();
      setBackendState({ status: "idle" });
      return;
    }

    registerCurrentVideo(currentVideo);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      clearPendingTimers();
    };
  }, [currentVideo, registerCurrentVideo, clearPendingTimers]);

  const retry = useCallback(() => {
    if (currentVideo) {
      registerCurrentVideo(currentVideo);
    }
  }, [currentVideo, registerCurrentVideo]);

  return {
    backendState,
    retry,
  };
}
