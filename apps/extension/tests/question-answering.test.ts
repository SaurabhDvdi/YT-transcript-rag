import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ApiClient } from "../services/api";

describe("Question Answering Integration in Extension Client", () => {
  const TEST_BASE_URL = "http://localhost:8787";
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient(TEST_BASE_URL, 1000);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends POST /api/v1/videos/:videoId/ask and parses grounded answer with citations", async () => {
    const mockResponse = {
      success: true,
      videoId: "Gfr50f6ZBvo",
      answer: {
        text: "The speaker explains the transformer self-attention mechanism.",
        grounded: true,
        citations: [
          {
            chunkId: "chunk_Gfr50f6ZBvo_0_1234",
            start: 120.5,
            end: 165.2,
          },
        ],
      },
      requestId: "server-req-id-ask",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": "server-req-id-ask",
        },
      }),
    );

    const res = await client.askQuestion("Gfr50f6ZBvo", "Explain attention mechanism", {
      topK: 5,
    });

    expect(res.success).toBe(true);
    expect(res.answer.grounded).toBe(true);
    expect(res.answer.text).toContain("transformer self-attention mechanism");
    expect(res.answer.citations).toHaveLength(1);
    const c0 = res.answer.citations[0]!;
    expect(c0.start).toBe(120.5);
    expect(c0.end).toBe(165.2);
  });

  it("handles no-evidence answer from server", async () => {
    const mockResponse = {
      success: true,
      videoId: "Gfr50f6ZBvo",
      answer: {
        text: "I couldn't find enough information in this video to answer that.",
        grounded: false,
        citations: [],
      },
      requestId: "server-req-id-no-evidence",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.askQuestion("Gfr50f6ZBvo", "How to bake a cake?");
    expect(res.success).toBe(true);
    expect(res.answer.grounded).toBe(false);
    expect(res.answer.citations).toHaveLength(0);
  });

  it("supports request cancellation via AbortController", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(
      client.askQuestion(
        "Gfr50f6ZBvo",
        "Question to abort",
        undefined,
        controller.signal,
      ),
    ).rejects.toThrow();
  });
});
