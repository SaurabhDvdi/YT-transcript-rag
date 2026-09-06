import type {
  StreamCitationEvent,
  StreamDoneEvent,
  StreamErrorEvent,
  StreamEvent,
  StreamStartEvent,
  StreamTokenEvent,
} from "@youtube-ai/shared-types";

export interface StreamHandlers {
  onStart?: (event: StreamStartEvent) => void;
  onToken?: (event: StreamTokenEvent) => void;
  onCitation?: (event: StreamCitationEvent) => void;
  onDone?: (event: StreamDoneEvent) => void;
  onError?: (event: StreamErrorEvent) => void;
}

/**
 * Parser for Server-Sent Events (SSE) protocol.
 * Correctly buffers split chunks and handles multiline frames.
 */
export class SSEParser {
  private buffer = "";

  constructor(private readonly handlers: StreamHandlers) {}

  /**
   * Feeds a decoded text chunk into the parser.
   */
  public feed(chunk: string): void {
    this.buffer += chunk;

    // SSE events are separated by double newlines (\n\n or \r\n\r\n)
    const normalized = this.buffer.replace(/\r\n/g, "\n");
    const blocks = normalized.split("\n\n");

    // The last element is the remaining incomplete block
    this.buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      this.processBlock(block);
    }
  }

  /**
   * Flushes any remaining data in the buffer.
   */
  public flush(): void {
    if (this.buffer.trim().length > 0) {
      this.processBlock(this.buffer);
      this.buffer = "";
    }
  }

  private processBlock(block: string): void {
    const lines = block.split("\n");
    let eventName = "";
    let dataStr = "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("event:")) {
        eventName = trimmed.slice(6).trim();
      } else if (trimmed.startsWith("data:")) {
        dataStr = trimmed.slice(5).trim();
      }
    }

    if (!dataStr) {
      return;
    }

    try {
      const parsed = JSON.parse(dataStr) as StreamEvent;
      const type = eventName || parsed.type;

      switch (type) {
        case "start":
          this.handlers.onStart?.(parsed as StreamStartEvent);
          break;
        case "token":
          this.handlers.onToken?.(parsed as StreamTokenEvent);
          break;
        case "citation":
          this.handlers.onCitation?.(parsed as StreamCitationEvent);
          break;
        case "done":
          this.handlers.onDone?.(parsed as StreamDoneEvent);
          break;
        case "error":
          this.handlers.onError?.(parsed as StreamErrorEvent);
          break;
      }
    } catch {
      // Ignore malformed JSON or heartbeat comments
    }
  }
}
