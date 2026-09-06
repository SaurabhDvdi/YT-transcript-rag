import { useState, useEffect, useCallback } from "react";
import type { VideoDetectionState, CurrentVideo } from "../types/youtube";
import { isExtensionMessage } from "../types/extension";
import { getTabVideo } from "../services/storage";

export function useCurrentVideo() {
  const [state, setState] = useState<VideoDetectionState>({
    status: "loading",
  });

  const queryActiveTabVideo = useCallback(async () => {
    setState({ status: "loading" });

    try {
      if (typeof browser === "undefined" || !browser.tabs) {
        setState({ status: "unsupported" });
        return;
      }

      const tabs = await browser.tabs.query({ active: true, currentWindow: true });
      const activeTab = tabs[0];

      if (!activeTab || !activeTab.id) {
        setState({ status: "unsupported" });
        return;
      }

      // Check tab storage cache first for instant response
      const cachedVideo = await getTabVideo(activeTab.id);
      if (cachedVideo) {
        setState({ status: "detected", video: cachedVideo });
      }

      // Query content script directly in the active tab for latest real-time status
      try {
        const response = (await browser.tabs.sendMessage(activeTab.id, {
          type: "GET_CURRENT_VIDEO",
        })) as { success: boolean; data?: CurrentVideo | null } | undefined;

        if (response && response.success && response.data) {
          setState({ status: "detected", video: response.data });
        } else if (response && response.success && response.data === null) {
          setState({ status: "unsupported" });
        } else if (!cachedVideo) {
          // Content script not loaded or not a YouTube page
          setState({ status: "unsupported" });
        }
      } catch {
        // Tab message failed (e.g. non-YouTube page where content script isn't injected)
        if (!cachedVideo) {
          setState({ status: "unsupported" });
        }
      }
    } catch (error) {
      console.warn("Error querying active tab video:", error);
      setState({
        status: "error",
        message: "Unable to communicate with the active browser tab.",
      });
    }
  }, []);

  useEffect(() => {
    // Initial query
    queryActiveTabVideo();

    if (typeof browser === "undefined") {
      return;
    }

    // 1. Listen for runtime messages from content script or background
    const handleMessage = (message: unknown, sender: unknown) => {
      if (!isExtensionMessage(message)) {
        return;
      }

      const msgSender = sender as { tab?: { id?: number } };

      // If we know the active tab, only process messages from the active tab
      browser.tabs
        .query({ active: true, currentWindow: true })
        .then((tabs) => {
          const activeTabId = tabs[0]?.id;
          if (msgSender.tab?.id && activeTabId && msgSender.tab.id !== activeTabId) {
            return;
          }

          if (message.type === "VIDEO_DETECTED") {
            setState({ status: "detected", video: message.payload });
          } else if (message.type === "VIDEO_CLEARED") {
            setState({ status: "unsupported" });
          }
        })
        .catch(() => {
          // Fallback for context without tabs query
          if (message.type === "VIDEO_DETECTED") {
            setState({ status: "detected", video: message.payload });
          } else if (message.type === "VIDEO_CLEARED") {
            setState({ status: "unsupported" });
          }
        });
    };

    browser.runtime.onMessage.addListener(handleMessage);

    // 2. Listen for tab activation changes (user switches tabs in browser)
    const handleTabActivated = () => {
      queryActiveTabVideo();
    };

    if (browser.tabs && browser.tabs.onActivated) {
      browser.tabs.onActivated.addListener(handleTabActivated);
    }

    // Teardown listeners on unmount
    return () => {
      browser.runtime.onMessage.removeListener(handleMessage);
      if (browser.tabs && browser.tabs.onActivated) {
        browser.tabs.onActivated.removeListener(handleTabActivated);
      }
    };
  }, [queryActiveTabVideo]);

  return {
    state,
    retry: queryActiveTabVideo,
  };
}
