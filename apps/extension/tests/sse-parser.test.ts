import { describe, it, expect, vi } from "vitest";
import { SSEParser } from "../services/sse-parser";

describe("SSEParser", () => {
  it("parses single token event correctly", () => {
    const onToken = vi.fn();
    const parser = new SSEParser({ onToken });

    parser.feed(`event: token\ndata: {"type":"token","text":"Hello world"}\n\n`);

    expect(onToken).toHaveBeenCalledTimes(1);
    expect(onToken).toHaveBeenCalledWith({
      type: "token",
      text: "Hello world",
    });
  });

  it("handles split network chunks across multiple feeds", () => {
    const onToken = vi.fn();
    const parser = new SSEParser({ onToken });

    // Chunk 1: partial header
    parser.feed("event: token\nda");
    expect(onToken).not.toHaveBeenCalled();

    // Chunk 2: rest of header and partial data
    parser.feed('ta: {"type":"token","te');
    expect(onToken).not.toHaveBeenCalled();

    // Chunk 3: end of event
    parser.feed('xt":"attention"}\n\n');
    expect(onToken).toHaveBeenCalledTimes(1);
    expect(onToken).toHaveBeenCalledWith({
      type: "token",
      text: "attention",
    });
  });

  it("handles multiple events in a single network chunk", () => {
    const onStart = vi.fn();
    const onToken = vi.fn();
    const onDone = vi.fn();
    const parser = new SSEParser({ onStart, onToken, onDone });

    const chunk = [
      `event: start\ndata: {"type":"start","requestId":"req_1","conversationId":"conv_1","messageId":"msg_1"}\n\n`,
      `event: token\ndata: {"type":"token","text":"Token 1"}\n\n`,
      `event: token\ndata: {"type":"token","text":"Token 2"}\n\n`,
      `event: done\ndata: {"type":"done","message":{"id":"msg_1","conversationId":"conv_1","role":"assistant","content":"Token 1Token 2","createdAt":"2026-09-05T00:00:00Z"}}\n\n`,
    ].join("");

    parser.feed(chunk);

    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onToken).toHaveBeenCalledTimes(2);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("handles citation and error events correctly", () => {
    const onCitation = vi.fn();
    const onError = vi.fn();
    const parser = new SSEParser({ onCitation, onError });

    parser.feed(
      `event: citation\ndata: {"type":"citation","citation":{"chunkId":"c1","start":10,"end":20,"text":"snippet"}}\n\n`,
    );
    expect(onCitation).toHaveBeenCalledWith({
      type: "citation",
      citation: { chunkId: "c1", start: 10, end: 20, text: "snippet" },
    });

    parser.feed(
      `event: error\ndata: {"type":"error","code":"STREAM_TIMEOUT","message":"Timed out"}\n\n`,
    );
    expect(onError).toHaveBeenCalledWith({
      type: "error",
      code: "STREAM_TIMEOUT",
      message: "Timed out",
    });
  });

  it("ignores malformed data lines gracefully", () => {
    const onToken = vi.fn();
    const parser = new SSEParser({ onToken });

    parser.feed(": keep-alive heartbeat comment\n\n");
    parser.feed("data: not-json\n\n");
    parser.feed(`data: {"type":"token","text":"Valid"}\n\n`);

    expect(onToken).toHaveBeenCalledTimes(1);
    expect(onToken).toHaveBeenCalledWith({
      type: "token",
      text: "Valid",
    });
  });
});
