import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useVideoBackend } from "../hooks/useVideoBackend";
import { apiClient, ApiClientError } from "../services/api";
import type { CurrentVideo } from "../types/youtube";

describe("Extension & Backend Integration", () => {
  const sampleVideoA: CurrentVideo = {
    videoId: "Gfr50f6ZBvo",
    title: "DeepMind Lecture",
    url: "https://www.youtube.com/watch?v=Gfr50f6ZBvo",
    type: "watch",
  };

  const sampleVideoB: CurrentVideo = {
    videoId: "dQw4w9WgXcQ",
    title: "Second Video",
    url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    type: "watch",
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers detected video and transitions backend state to connected", async () => {
    vi.spyOn(apiClient, "registerVideo").mockResolvedValueOnce({
      success: true,
      video: {
        videoId: "Gfr50f6ZBvo",
        status: "accepted",
      },
      requestId: "req-integration-123",
    });

    const { result } = renderHook(() => useVideoBackend(sampleVideoA));

    expect(result.current.backendState.status).toBe("registering");

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("connected");
    });

    if (result.current.backendState.status === "connected") {
      expect(result.current.backendState.videoId).toBe("Gfr50f6ZBvo");
      expect(result.current.backendState.processingStatus).toBe("accepted");
      expect(result.current.backendState.requestId).toBe("req-integration-123");
    }
  });

  it("handles backend unavailable without breaking video detection", async () => {
    vi.spyOn(apiClient, "registerVideo").mockRejectedValueOnce(
      new ApiClientError(
        "Network connection failed",
        "NETWORK_ERROR",
        0,
        undefined,
        "Cannot connect to the server. Please verify your backend is running.",
      ),
    );

    const { result } = renderHook(() => useVideoBackend(sampleVideoA));

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("error");
    });

    if (result.current.backendState.status === "error") {
      expect(result.current.backendState.videoId).toBe("Gfr50f6ZBvo");
      expect(result.current.backendState.message).toContain(
        "Cannot connect to the server",
      );
    }
  });

  it("handles SPA navigation by registering the new video without retaining stale state", async () => {
    const registerSpy = vi.spyOn(apiClient, "registerVideo");

    registerSpy.mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "accepted" },
      requestId: "req-video-a",
    });

    const { result, rerender } = renderHook(({ video }) => useVideoBackend(video), {
      initialProps: { video: sampleVideoA },
    });

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("connected");
    });

    // Mock response for Video B
    registerSpy.mockResolvedValueOnce({
      success: true,
      video: { videoId: "dQw4w9WgXcQ", status: "accepted" },
      requestId: "req-video-b",
    });

    // Simulate YouTube SPA navigation to Video B
    rerender({ video: sampleVideoB });

    await waitFor(() => {
      if (result.current.backendState.status === "connected") {
        expect(result.current.backendState.videoId).toBe("dQw4w9WgXcQ");
        expect(result.current.backendState.requestId).toBe("req-video-b");
      }
    });

    expect(registerSpy).toHaveBeenCalledTimes(2);
    expect(registerSpy).toHaveBeenLastCalledWith(
      { videoId: "dQw4w9WgXcQ" },
      expect.any(Object),
    );
  });

  it("resets state to idle when navigating away from video page", async () => {
    vi.spyOn(apiClient, "registerVideo").mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "accepted" },
      requestId: "req-video-a",
    });

    const { result, rerender } = renderHook(
      ({ video }: { video: CurrentVideo | null }) => useVideoBackend(video),
      { initialProps: { video: sampleVideoA as CurrentVideo | null } },
    );

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("connected");
    });

    // Navigate to homepage / non-video
    rerender({ video: null });

    expect(result.current.backendState.status).toBe("idle");
  });

  it("supports explicit user retry upon error", async () => {
    const registerSpy = vi.spyOn(apiClient, "registerVideo");

    // First attempt fails
    registerSpy.mockRejectedValueOnce(new ApiClientError("Offline", "NETWORK_ERROR", 0));

    const { result } = renderHook(() => useVideoBackend(sampleVideoA));

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("error");
    });

    // Second attempt (after retry) succeeds
    registerSpy.mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "accepted" },
      requestId: "req-retry-success",
    });

    act(() => {
      result.current.retry();
    });

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("connected");
    });

    expect(registerSpy).toHaveBeenCalledTimes(2);
  });

  it("polls status until transcript becomes ready and stores summary metadata", async () => {
    vi.spyOn(apiClient, "registerVideo").mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "processing" },
      requestId: "req-poll-1",
    });

    const statusSpy = vi.spyOn(apiClient, "getVideoStatus");
    // First poll returns still processing
    statusSpy.mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "processing" },
      requestId: "req-poll-2",
    });
    // Second poll returns ready with transcript summary
    statusSpy.mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "ready" },
      transcript: {
        language: "English",
        languageCode: "en",
        isAutoGenerated: false,
        segmentCount: 42,
        duration: 320.5,
      },
      requestId: "req-poll-3",
    });

    const { result } = renderHook(() => useVideoBackend(sampleVideoA));

    await waitFor(() => {
      expect(result.current.backendState.status).toBe("connected");
    });

    if (result.current.backendState.status === "connected") {
      expect(result.current.backendState.processingStatus).toBe("processing");
    }

    // Wait for polling loop to reach terminal 'ready' state
    await waitFor(
      () => {
        expect(result.current.backendState.status).toBe("connected");
        if (result.current.backendState.status === "connected") {
          expect(result.current.backendState.processingStatus).toBe("ready");
          expect(result.current.backendState.transcript?.segmentCount).toBe(42);
          expect(result.current.backendState.transcript?.language).toBe("English");
        }
      },
      { timeout: 4000 },
    );
  });

  it("stops polling immediately when status becomes unavailable", async () => {
    vi.spyOn(apiClient, "registerVideo").mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "processing" },
      requestId: "req-unavail-1",
    });

    vi.spyOn(apiClient, "getVideoStatus").mockResolvedValueOnce({
      success: true,
      video: { videoId: "Gfr50f6ZBvo", status: "unavailable" },
      requestId: "req-unavail-2",
    });

    const { result } = renderHook(() => useVideoBackend(sampleVideoA));

    await waitFor(
      () => {
        expect(result.current.backendState.status).toBe("connected");
        if (result.current.backendState.status === "connected") {
          expect(result.current.backendState.processingStatus).toBe("unavailable");
        }
      },
      { timeout: 3000 },
    );
  });
});
