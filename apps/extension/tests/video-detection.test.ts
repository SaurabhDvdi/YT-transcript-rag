import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { VideoDetectionState, CurrentVideo } from "../types/youtube";
import {
  extractPageTitle,
  extractCurrentVideoFromPage,
  subscribeToYouTubeNavigation,
} from "../services/youtube";

describe("Video Detection & Title Extraction", () => {
  beforeEach(() => {
    document.head.innerHTML = "";
    document.body.innerHTML = "";
    document.title = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Title Extraction Fallback Hierarchy", () => {
    it("prefers structured meta[name='title'] when present", () => {
      const meta = document.createElement("meta");
      meta.setAttribute("name", "title");
      meta.setAttribute("content", "Attention Is All You Need - Deep Learning Explained");
      document.head.appendChild(meta);

      document.title = "Fallback Document Title - YouTube";

      const title = extractPageTitle();
      expect(title).toBe("Attention Is All You Need - Deep Learning Explained");
    });

    it("uses meta[property='og:title'] if meta[name='title'] is absent", () => {
      const meta = document.createElement("meta");
      meta.setAttribute("property", "og:title");
      meta.setAttribute("content", "Building RAG from Scratch");
      document.head.appendChild(meta);

      const title = extractPageTitle();
      expect(title).toBe("Building RAG from Scratch");
    });

    it("falls back to document.title and strips YouTube branding suffix", () => {
      document.title = "DeepSeek vs Claude 3.5 Sonnet Benchmark - YouTube";

      const title = extractPageTitle();
      expect(title).toBe("DeepSeek vs Claude 3.5 Sonnet Benchmark");
    });

    it("falls back to DOM element when metadata and document.title are missing or default", () => {
      document.title = "YouTube"; // Generic YouTube title
      const h1 = document.createElement("h1");
      h1.className = "ytd-watch-metadata";
      h1.textContent = "Visible Heading Title - YouTube";
      document.body.appendChild(h1);

      const title = extractPageTitle();
      expect(title).toBe("Visible Heading Title");
    });

    it("returns null safely when no title can be resolved without crashing", () => {
      document.title = "";
      const title = extractPageTitle();
      expect(title).toBeNull();
    });
  });

  describe("extractCurrentVideoFromPage", () => {
    it("returns null when window.location is a non-video page", () => {
      // Vitest jsdom default is usually http://localhost:3000/
      const video = extractCurrentVideoFromPage();
      expect(video).toBeNull();
    });
  });

  describe("SPA Navigation Subscription & Event Teardown", () => {
    it("registers listeners and unregisters cleanly when unsubscribed", () => {
      const addEventListenerSpy = vi.spyOn(window, "addEventListener");
      const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

      const callback = vi.fn();
      const unsubscribe = subscribeToYouTubeNavigation(callback);

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "yt-navigate-finish",
        expect.any(Function),
        expect.any(Object),
      );
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "yt-page-data-updated",
        expect.any(Function),
        expect.any(Object),
      );
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "popstate",
        expect.any(Function),
        expect.any(Object),
      );

      unsubscribe();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "yt-navigate-finish",
        expect.any(Function),
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "yt-page-data-updated",
        expect.any(Function),
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "popstate",
        expect.any(Function),
      );
    });
  });
});

describe("State Transitions (VideoDetectionState)", () => {
  // Pure state transition reducer simulator to verify domain state machine logic
  function transitionState(
    current: VideoDetectionState,
    action:
      | { type: "START_DETECTION" }
      | { type: "DETECTED"; video: CurrentVideo }
      | { type: "UNSUPPORTED" }
      | { type: "ERROR"; message: string },
  ): VideoDetectionState {
    switch (action.type) {
      case "START_DETECTION":
        return { status: "loading" };
      case "DETECTED":
        return { status: "detected", video: action.video };
      case "UNSUPPORTED":
        return { status: "unsupported" };
      case "ERROR":
        return { status: "error", message: action.message };
    }
  }

  const sampleVideoA: CurrentVideo = {
    videoId: "Gfr50f6ZBvo",
    title: "Video A",
    url: "https://www.youtube.com/watch?v=Gfr50f6ZBvo",
    type: "watch",
  };

  const sampleVideoB: CurrentVideo = {
    videoId: "dQw4w9WgXcQ",
    title: "Video B",
    url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    type: "watch",
  };

  it("handles unsupported -> detected transition", () => {
    let state: VideoDetectionState = { status: "unsupported" };
    state = transitionState(state, { type: "DETECTED", video: sampleVideoA });

    expect(state).toEqual({
      status: "detected",
      video: sampleVideoA,
    });
  });

  it("handles detected -> detected with different video (SPA navigation)", () => {
    let state: VideoDetectionState = {
      status: "detected",
      video: sampleVideoA,
    };

    // User clicks another video in YouTube SPA
    state = transitionState(state, { type: "DETECTED", video: sampleVideoB });

    expect(state.status).toBe("detected");
    if (state.status === "detected") {
      expect(state.video.videoId).toBe("dQw4w9WgXcQ");
      expect(state.video.title).toBe("Video B");
    }
  });

  it("handles detected -> unsupported transition (navigating away from video)", () => {
    let state: VideoDetectionState = {
      status: "detected",
      video: sampleVideoA,
    };

    // User navigates to YouTube home or non-video page
    state = transitionState(state, { type: "UNSUPPORTED" });
    expect(state).toEqual({ status: "unsupported" });
  });

  it("handles loading -> detected transition", () => {
    let state: VideoDetectionState = { status: "loading" };
    state = transitionState(state, { type: "DETECTED", video: sampleVideoA });

    expect(state).toEqual({
      status: "detected",
      video: sampleVideoA,
    });
  });

  it("handles loading -> error transition", () => {
    let state: VideoDetectionState = { status: "loading" };
    state = transitionState(state, {
      type: "ERROR",
      message: "Unable to detect the current YouTube video.",
    });

    expect(state).toEqual({
      status: "error",
      message: "Unable to detect the current YouTube video.",
    });
  });
});
