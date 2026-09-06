/**
 * Session management for pseudonymous rate limiting and quota accounting.
 * Generates and persists a UUID in chrome.storage.local (with localStorage / in-memory fallback).
 */

const SESSION_KEY = "yt_ai_session_id";
let memorySessionId: string | null = null;

/**
 * Retrieves the existing persistent pseudonymous session UUID or creates and stores a new one.
 */
export async function getOrCreateSessionId(): Promise<string> {
  if (memorySessionId) {
    return memorySessionId;
  }

  // 1. Try chrome.storage.local
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    try {
      const result = await chrome.storage.local.get(SESSION_KEY);
      if (result[SESSION_KEY] && typeof result[SESSION_KEY] === "string") {
        memorySessionId = result[SESSION_KEY];
        return memorySessionId;
      }
      const newId = crypto.randomUUID();
      await chrome.storage.local.set({ [SESSION_KEY]: newId });
      memorySessionId = newId;
      return memorySessionId;
    } catch {
      // Fall through to localStorage/in-memory
    }
  }

  // 2. Try window.localStorage
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const stored = window.localStorage.getItem(SESSION_KEY);
      if (stored) {
        memorySessionId = stored;
        return memorySessionId;
      }
      const newId = crypto.randomUUID();
      window.localStorage.setItem(SESSION_KEY, newId);
      memorySessionId = newId;
      return memorySessionId;
    } catch {
      // Fall through to in-memory
    }
  }

  // 3. In-memory fallback
  if (!memorySessionId) {
    memorySessionId = crypto.randomUUID();
  }
  return memorySessionId;
}

/**
 * Synchronously returns the currently cached session ID or generates a fallback.
 */
export function getSessionIdSync(): string {
  if (memorySessionId) {
    return memorySessionId;
  }
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const stored = window.localStorage.getItem(SESSION_KEY);
      if (stored) {
        memorySessionId = stored;
        return memorySessionId;
      }
    } catch {
      // Ignore
    }
  }
  memorySessionId = crypto.randomUUID();
  return memorySessionId;
}
