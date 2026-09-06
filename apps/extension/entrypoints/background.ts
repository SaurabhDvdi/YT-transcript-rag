import { setTabVideo, setLastActiveVideo } from "../services/storage";
import { isExtensionMessage } from "../types/extension";

export default defineBackground(() => {
  // 1. Cross-browser side panel action setup
  try {
    if (import.meta.env.BROWSER === "firefox") {
      // Firefox sidebarAction integration
      if (browser.action && browser.action.onClicked) {
        browser.action.onClicked.addListener(async () => {
          if (browser.sidebarAction && typeof browser.sidebarAction.open === "function") {
            await browser.sidebarAction.open();
          }
        });
      }
    } else {
      // Chromium sidePanel native open-on-action-click behavior
      if (
        typeof chrome !== "undefined" &&
        chrome.sidePanel &&
        typeof chrome.sidePanel.setPanelBehavior === "function"
      ) {
        chrome.sidePanel
          .setPanelBehavior({ openPanelOnActionClick: true })
          .catch(() => {});
      }
    }
  } catch (error) {
    console.warn("Could not configure side panel action behavior:", error);
  }

  // 2. Track video state messages dispatched from content scripts
  browser.runtime.onMessage.addListener((message: unknown, sender: unknown) => {
    if (!isExtensionMessage(message)) {
      return;
    }

    const msgSender = sender as { tab?: { id?: number } };
    const tabId = msgSender.tab?.id;

    if (message.type === "VIDEO_DETECTED") {
      if (typeof tabId === "number") {
        setTabVideo(tabId, message.payload);
      }
      setLastActiveVideo(message.payload);
    } else if (message.type === "VIDEO_CLEARED") {
      if (typeof tabId === "number") {
        setTabVideo(tabId, null);
      }
    }
  });

  // 3. Clean up tab state when tabs are closed
  if (browser.tabs && browser.tabs.onRemoved) {
    browser.tabs.onRemoved.addListener((tabId: number) => {
      setTabVideo(tabId, null);
    });
  }
});
