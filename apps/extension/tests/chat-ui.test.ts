import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ApiClient } from "../services/api";

describe("Conversational API Integration in Extension Client", () => {
  const TEST_BASE_URL = "http://localhost:8787";
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient(TEST_BASE_URL, 1000);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a conversation via POST /api/v1/videos/:videoId/conversations", async () => {
    const mockResponse = {
      success: true,
      conversation: {
        id: "conv_client_test",
        videoId: "Gfr50f6ZBvo",
        title: "New Conversation",
        titleSource: "auto",
        createdAt: "2026-09-01T10:00:00.000Z",
        updatedAt: "2026-09-01T10:00:00.000Z",
      },
      requestId: "req_conv_create",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.createConversation("Gfr50f6ZBvo");
    expect(res.success).toBe(true);
    expect(res.conversation.id).toBe("conv_client_test");
    expect(res.conversation.videoId).toBe("Gfr50f6ZBvo");
  });

  it("fetches conversation detail with messages via GET /api/v1/conversations/:id", async () => {
    const mockResponse = {
      success: true,
      conversation: {
        id: "conv_client_test",
        videoId: "Gfr50f6ZBvo",
        title: "Attention Discussion",
        titleSource: "auto",
        createdAt: "2026-09-01T10:00:00.000Z",
        updatedAt: "2026-09-01T10:05:00.000Z",
      },
      messages: [
        {
          id: "msg_1",
          conversationId: "conv_client_test",
          role: "user",
          content: "What is attention?",
          createdAt: "2026-09-01T10:00:00.000Z",
        },
        {
          id: "msg_2",
          conversationId: "conv_client_test",
          role: "assistant",
          content: "Attention allows weighting tokens [00:10 - 00:25].",
          grounded: true,
          citations: [{ chunkId: "c_1", start: 10, end: 25 }],
          createdAt: "2026-09-01T10:01:00.000Z",
        },
      ],
      requestId: "req_conv_get",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.getConversation("conv_client_test");
    expect(res.success).toBe(true);
    expect(res.messages).toHaveLength(2);
    expect(res.messages[0]?.role).toBe("user");
    expect(res.messages[1]?.role).toBe("assistant");
    expect(res.messages[1]?.citations).toHaveLength(1);
  });

  it("submits conversational askQuestion with conversationId and clientRequestId", async () => {
    const mockResponse = {
      success: true,
      videoId: "Gfr50f6ZBvo",
      conversationId: "conv_client_test",
      answer: {
        text: "Self-attention is useful for long sequences.",
        grounded: true,
        citations: [],
      },
      message: {
        id: "msg_turn_2",
        role: "assistant",
        text: "Self-attention is useful for long sequences.",
        grounded: true,
        citations: [],
      },
      requestId: "req_ask_conv",
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.askQuestion("Gfr50f6ZBvo", "Why is it useful?", {
      conversationId: "conv_client_test",
      clientRequestId: "unique_req_999",
      topK: 5,
    });

    expect(res.success).toBe(true);
    expect(res.conversationId).toBe("conv_client_test");
    expect(res.message?.id).toBe("msg_turn_2");

    const calledBody = JSON.parse(fetchSpy.mock.calls[0]![1]!.body as string);
    expect(calledBody.conversationId).toBe("conv_client_test");
    expect(calledBody.clientRequestId).toBe("unique_req_999");
  });

  it("updates conversation title via PATCH /api/v1/conversations/:id", async () => {
    const mockResponse = {
      success: true,
      conversation: {
        id: "conv_client_test",
        videoId: "Gfr50f6ZBvo",
        title: "Renamed Title",
        titleSource: "user",
        createdAt: "2026-09-01T10:00:00.000Z",
        updatedAt: "2026-09-01T10:10:00.000Z",
      },
      requestId: "req_patch",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.updateConversationTitle(
      "conv_client_test",
      "Renamed Title",
      "Gfr50f6ZBvo",
    );
    expect(res.success).toBe(true);
    expect(res.conversation.title).toBe("Renamed Title");
    expect(res.conversation.titleSource).toBe("user");
  });

  it("deletes conversation via DELETE /api/v1/conversations/:id", async () => {
    const mockResponse = {
      success: true,
      conversationId: "conv_client_test",
      requestId: "req_del",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const res = await client.deleteConversation("conv_client_test", "Gfr50f6ZBvo");
    expect(res.success).toBe(true);
    expect(res.conversationId).toBe("conv_client_test");
  });

  it("streams answer via streamQuestion with SSE events", async () => {
    const sseBody = [
      `event: start\ndata: {"type":"start","requestId":"req_s","conversationId":"conv_s","messageId":"msg_s"}\n\n`,
      `event: token\ndata: {"type":"token","text":"Streamed answer"}\n\n`,
      `event: done\ndata: {"type":"done","message":{"id":"msg_s","conversationId":"conv_s","role":"assistant","content":"Streamed answer","createdAt":"2026-09-05T00:00:00Z"}}\n\n`,
    ].join("");

    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(ctrl) {
        ctrl.enqueue(encoder.encode(sseBody));
        ctrl.close();
      },
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const tokens: string[] = [];
    let isDone = false;

    await client.streamQuestion(
      "Gfr50f6ZBvo",
      "Stream this",
      { conversationId: "conv_s" },
      {
        onToken(e) {
          tokens.push(e.text);
        },
        onDone() {
          isDone = true;
        },
      },
    );

    expect(tokens).toEqual(["Streamed answer"]);
    expect(isDone).toBe(true);
  });
});
