import {
  extractCurrentVideoFromPage,
  subscribeToYouTubeNavigation,
} from "../services/youtube";
import { isExtensionMessage, type ExtensionMessage } from "../types/extension";
import type { CurrentVideo } from "../types/youtube";

export default defineContentScript({
  matches: ["*://*.youtube.com/*"],
  runAt: "document_idle",
  main(ctx) {
    // 1. Subscribe to YouTube SPA navigation and metadata updates
    const unsubscribe = subscribeToYouTubeNavigation((video: CurrentVideo | null) => {
      try {
        if (video) {
          const message: ExtensionMessage = {
            type: "VIDEO_DETECTED",
            payload: video,
          };
          browser.runtime.sendMessage(message).catch(() => {
            // Extension context might be invalidated during reload; fail safely
          });
        } else {
          const message: ExtensionMessage = {
            type: "VIDEO_CLEARED",
          };
          browser.runtime.sendMessage(message).catch(() => {
            // Fail safely
          });
        }
      } catch {
        // Ignore runtime context errors
      }
    });

    // 2. Respond to direct queries and actions from side panel
    const handleMessage = (message: unknown) => {
      if (isExtensionMessage(message)) {
        if (message.type === "GET_CURRENT_VIDEO") {
          const currentVideo = extractCurrentVideoFromPage();
          return Promise.resolve({ success: true, data: currentVideo });
        }
        if (message.type === "SEEK_VIDEO") {
          const videoElement = document.querySelector("video");
          if (
            videoElement &&
            typeof message.timestamp === "number" &&
            !isNaN(message.timestamp)
          ) {
            videoElement.currentTime = message.timestamp;
            videoElement.play().catch(() => {});
            return Promise.resolve({ success: true, data: { time: message.timestamp } });
          }
          return Promise.resolve({ success: false, error: "Video element not found" });
        }
      }
    };

    browser.runtime.onMessage.addListener(handleMessage);

    // 3. Teardown lifecycle hook provided by WXT
    ctx.onInvalidated(() => {
      unsubscribe();
      browser.runtime.onMessage.removeListener(handleMessage);
    });
  },
});
