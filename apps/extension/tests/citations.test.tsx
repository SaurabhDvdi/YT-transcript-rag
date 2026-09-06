import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CitationChip, formatTimestamp } from "../components/CitationChip";
import { formatAnswerForCopy } from "../utils/markdown";
import type { Citation } from "@youtube-ai/shared-types";

describe("Citation and Timestamp Systems", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("formatTimestamp", () => {
    it("formats sub-minute seconds correctly", () => {
      expect(formatTimestamp(5)).toBe("00:05");
      expect(formatTimestamp(45)).toBe("00:45");
    });

    it("formats minutes and seconds (MM:SS)", () => {
      expect(formatTimestamp(75)).toBe("01:15");
      expect(formatTimestamp(600)).toBe("10:00");
      expect(formatTimestamp(1199)).toBe("19:59");
    });

    it("formats hour-level timestamps (HH:MM:SS)", () => {
      expect(formatTimestamp(3600)).toBe("1:00:00");
      expect(formatTimestamp(3665)).toBe("1:01:05");
      expect(formatTimestamp(7325)).toBe("2:02:05");
    });

    it("handles zero and negative gracefully", () => {
      expect(formatTimestamp(0)).toBe("00:00");
      expect(formatTimestamp(-10)).toBe("00:00");
    });
  });

  describe("formatAnswerForCopy", () => {
    const citations: Citation[] = [
      { chunkId: "c1", start: 75, end: 90, score: 0.95 },
      { chunkId: "c2", start: 180, end: 210, score: 0.88 },
    ];

    it("resolves [E1] markers into readable timestamps and appends sources", () => {
      const input =
        "Attention allows routing information across tokens [E1] and layer heads [E2].";
      const formatted = formatAnswerForCopy(input, citations);

      expect(formatted).toContain("[01:15–01:30]");
      expect(formatted).toContain("[03:00–03:30]");
      expect(formatted).not.toContain("[E1]");
      expect(formatted).not.toContain("[E2]");
      expect(formatted).toContain("---");
      expect(formatted).toContain("Source 1: 01:15–01:30");
      expect(formatted).toContain("Source 2: 03:00–03:30");
    });

    it("cleans phantom [E#] tags if no citations exist", () => {
      const input = "This is an answer without citations [E1].";
      const formatted = formatAnswerForCopy(input);

      expect(formatted).toBe("This is an answer without citations .");
    });
  });

  describe("CitationChip Component", () => {
    const citation: Citation = {
      chunkId: "chunk_test",
      start: 125,
      end: 140,
    };

    it("renders formatted timestamp badge and index", () => {
      render(<CitationChip citation={citation} />);

      expect(screen.getByText(/02:05/)).toBeDefined();
      expect(screen.getByText(/02:20/)).toBeDefined();
    });

    it("dispatches SEEK_VIDEO message to the active YouTube tab when clicked", async () => {
      const sendMessageMock = vi.fn((tabId, msg, cb) => {
        if (cb) cb({ success: true });
      });
      const queryMock = vi
        .fn()
        .mockResolvedValue([{ id: 101, url: "https://www.youtube.com/watch?v=123" }]);

      (globalThis as unknown as { chrome: unknown }).chrome = {
        tabs: {
          query: queryMock,
          sendMessage: sendMessageMock,
        },
      };

      render(<CitationChip citation={citation} />);
      const btn = screen.getByRole("button");
      fireEvent.click(btn);

      await waitFor(() => {
        expect(queryMock).toHaveBeenCalled();
        expect(sendMessageMock).toHaveBeenCalledWith(
          101,
          { type: "SEEK_VIDEO", timestamp: 125 },
          expect.any(Function),
        );
      });
    });

    it("reveals tooltip on mouse enter and hides on mouse leave", () => {
      render(<CitationChip citation={citation} />);
      const btn = screen.getByRole("button");

      fireEvent.mouseEnter(btn);
      expect(screen.getByRole("tooltip")).toBeDefined();
      expect(screen.getByText("Verified Transcript Segment")).toBeDefined();

      fireEvent.mouseLeave(btn);
      expect(screen.queryByRole("tooltip")).toBeNull();
    });
  });
});
