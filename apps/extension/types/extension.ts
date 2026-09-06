import type { CurrentVideo } from "./youtube";

/**
 * Strongly typed messages dispatched across extension contexts
 * (Content Script <-> Background Service Worker <-> Side Panel).
 */
export type ExtensionMessage =
  | { type: "VIDEO_DETECTED"; payload: CurrentVideo }
  | { type: "VIDEO_CLEARED" }
  | { type: "GET_CURRENT_VIDEO" }
  | { type: "CURRENT_VIDEO_RESPONSE"; payload: CurrentVideo | null }
  | { type: "SEEK_VIDEO"; timestamp: number };

/**
 * Standard typed response contract for message handlers.
 */
export type ExtensionResponse<T = unknown> =
  { success: true; data: T } | { success: false; error: string };

/**
 * Type guard to safely validate unknown incoming messages.
 */
export function isExtensionMessage(value: unknown): value is ExtensionMessage {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as { type?: unknown };
  return (
    candidate.type === "VIDEO_DETECTED" ||
    candidate.type === "VIDEO_CLEARED" ||
    candidate.type === "GET_CURRENT_VIDEO" ||
    candidate.type === "CURRENT_VIDEO_RESPONSE" ||
    candidate.type === "SEEK_VIDEO"
  );
}
