import type { CurrentVideo } from "../types/youtube";

const STORAGE_KEYS = {
  LAST_ACTIVE_VIDEO: "yt_ai_last_active_video",
  TAB_VIDEO_PREFIX: "yt_ai_tab_video_",
} as const;

// In-memory fallback for environments without browser.storage (e.g., unit tests)
const memoryFallback = new Map<string, unknown>();

/**
 * Checks if browser extension storage is available.
 */
function isStorageAvailable(): boolean {
  return (
    typeof browser !== "undefined" &&
    Boolean(browser.storage) &&
    Boolean(browser.storage.local)
  );
}

/**
 * Persists the latest active video to extension storage.
 */
export async function setLastActiveVideo(video: CurrentVideo | null): Promise<void> {
  try {
    if (isStorageAvailable()) {
      if (video) {
        await browser.storage.local.set({ [STORAGE_KEYS.LAST_ACTIVE_VIDEO]: video });
      } else {
        await browser.storage.local.remove(STORAGE_KEYS.LAST_ACTIVE_VIDEO);
      }
    } else {
      if (video) {
        memoryFallback.set(STORAGE_KEYS.LAST_ACTIVE_VIDEO, video);
      } else {
        memoryFallback.delete(STORAGE_KEYS.LAST_ACTIVE_VIDEO);
      }
    }
  } catch (error) {
    console.warn("Failed to persist active video to storage:", error);
  }
}

/**
 * Retrieves the last active video from extension storage.
 */
export async function getLastActiveVideo(): Promise<CurrentVideo | null> {
  try {
    if (isStorageAvailable()) {
      const result = await browser.storage.local.get(STORAGE_KEYS.LAST_ACTIVE_VIDEO);
      return (result[STORAGE_KEYS.LAST_ACTIVE_VIDEO] as CurrentVideo) ?? null;
    } else {
      return (memoryFallback.get(STORAGE_KEYS.LAST_ACTIVE_VIDEO) as CurrentVideo) ?? null;
    }
  } catch (error) {
    console.warn("Failed to retrieve active video from storage:", error);
    return null;
  }
}

/**
 * Associates a detected video with a specific browser tab ID.
 */
export async function setTabVideo(
  tabId: number,
  video: CurrentVideo | null,
): Promise<void> {
  const key = `${STORAGE_KEYS.TAB_VIDEO_PREFIX}${tabId}`;
  try {
    if (isStorageAvailable()) {
      if (video) {
        await browser.storage.local.set({ [key]: video });
      } else {
        await browser.storage.local.remove(key);
      }
    } else {
      if (video) {
        memoryFallback.set(key, video);
      } else {
        memoryFallback.delete(key);
      }
    }
  } catch (error) {
    console.warn(`Failed to store video for tab ${tabId}:`, error);
  }
}

/**
 * Retrieves the video associated with a specific browser tab ID.
 */
export async function getTabVideo(tabId: number): Promise<CurrentVideo | null> {
  const key = `${STORAGE_KEYS.TAB_VIDEO_PREFIX}${tabId}`;
  try {
    if (isStorageAvailable()) {
      const result = await browser.storage.local.get(key);
      return (result[key] as CurrentVideo) ?? null;
    } else {
      return (memoryFallback.get(key) as CurrentVideo) ?? null;
    }
  } catch (error) {
    console.warn(`Failed to retrieve video for tab ${tabId}:`, error);
    return null;
  }
}

const CONVERSATION_PREFIX = "yt_ai_conv_";

/**
 * Retrieves the stored conversation ID associated with a video.
 */
export async function getVideoConversationId(videoId: string): Promise<string | null> {
  const key = `${CONVERSATION_PREFIX}${videoId}`;
  try {
    if (isStorageAvailable()) {
      const result = await browser.storage.local.get(key);
      return (result[key] as string) ?? null;
    } else {
      return (memoryFallback.get(key) as string) ?? null;
    }
  } catch {
    return null;
  }
}

/**
 * Associates or removes a conversation ID for a video.
 */
export async function setVideoConversationId(
  videoId: string,
  conversationId: string | null,
): Promise<void> {
  const key = `${CONVERSATION_PREFIX}${videoId}`;
  try {
    if (isStorageAvailable()) {
      if (conversationId) {
        await browser.storage.local.set({ [key]: conversationId });
      } else {
        await browser.storage.local.remove(key);
      }
    } else {
      if (conversationId) {
        memoryFallback.set(key, conversationId);
      } else {
        memoryFallback.delete(key);
      }
    }
  } catch {
    // Non-blocking storage fallback
  }
}
