import type { CurrentVideo } from "../types/youtube";
import { extractYouTubeVideoId, extractYouTubeVideoType } from "../utils/url";

/**
 * Strips YouTube branding suffix (e.g., " - YouTube") from title string.
 */
function sanitizeTitle(rawTitle: string | null | undefined): string | null {
  if (!rawTitle) return null;
  const trimmed = rawTitle.trim();
  if (!trimmed) return null;
  // Remove trailing " - YouTube" or " | YouTube"
  const cleaned = trimmed.replace(/\s*[-–—|]\s*YouTube$/i, "").trim();
  return cleaned.length > 0 ? cleaned : null;
}

/**
 * Safely extracts the YouTube video title using a prioritized fallback hierarchy:
 * 1. Document metadata / meta tags (meta[name="title"], meta[property="og:title"])
 * 2. Cleaned document.title
 * 3. YouTube DOM title element (ytd-watch-metadata #title, #title h1)
 *
 * Never throws; returns null if unavailable.
 */
export function extractPageTitle(): string | null {
  try {
    // 1. Structured metadata
    const metaTitle =
      document.querySelector('meta[name="title"]')?.getAttribute("content") ||
      document.querySelector('meta[property="og:title"]')?.getAttribute("content");
    const sanitizedMeta = sanitizeTitle(metaTitle);
    if (sanitizedMeta) {
      return sanitizedMeta;
    }

    // 2. Document title fallback
    const docTitle = sanitizeTitle(document.title);
    if (docTitle && docTitle.toLowerCase() !== "youtube") {
      return docTitle;
    }

    // 3. Lightweight visible DOM fallback
    const domSelectors = [
      "ytd-watch-metadata #title h1",
      "#title h1 yt-formatted-string",
      "h1.ytd-watch-metadata",
      "h1.title.style-scope.ytd-video-primary-info-renderer",
    ];

    for (const selector of domSelectors) {
      const element = document.querySelector(selector);
      if (element && element.textContent) {
        const text = sanitizeTitle(element.textContent);
        if (text) return text;
      }
    }
  } catch {
    // Fail gracefully without crashing
    return null;
  }

  return null;
}

/**
 * Extracts normalized current video information from the active window.
 * Returns null if the page is not a recognized YouTube video.
 */
export function extractCurrentVideoFromPage(): CurrentVideo | null {
  try {
    if (typeof window === "undefined" || !window.location) {
      return null;
    }

    const currentUrl = window.location.href;
    const videoId = extractYouTubeVideoId(currentUrl);
    const videoType = extractYouTubeVideoType(currentUrl);

    if (!videoId || !videoType) {
      return null;
    }

    const title = extractPageTitle();

    return {
      videoId,
      title,
      url: currentUrl,
      type: videoType,
    };
  } catch {
    return null;
  }
}

/**
 * Subscribes to YouTube SPA navigation lifecycle events.
 * Handles SPA navigation (Video A -> Video B) without page reloads.
 *
 * Listens for:
 * - 'yt-navigate-finish' (YouTube internal SPA finish)
 * - 'yt-page-data-updated' (Metadata rendered)
 * - 'popstate' (Browser back/forward)
 * - Title tag MutationObserver (Lightweight title change detection)
 *
 * @param callback Called whenever the detected video changes or transitions to unsupported.
 * @returns Cleanup function to disconnect observers and unregister event listeners.
 */
export function subscribeToYouTubeNavigation(
  callback: (video: CurrentVideo | null) => void,
): () => void {
  let lastVideoId: string | null = null;
  let lastTitle: string | null = null;

  const checkAndUpdate = () => {
    const video = extractCurrentVideoFromPage();
    const currentVideoId = video?.videoId ?? null;
    const currentTitle = video?.title ?? null;

    // Trigger update if video ID changed, or title arrived for the same video ID
    if (
      currentVideoId !== lastVideoId ||
      (currentVideoId !== null && currentTitle !== lastTitle)
    ) {
      lastVideoId = currentVideoId;
      lastTitle = currentTitle;
      callback(video);
    }
  };

  // Immediate initial check
  checkAndUpdate();

  const handleYtNavigateFinish = () => {
    checkAndUpdate();
    // YouTube title sometimes resolves slightly after navigation finish event
    setTimeout(checkAndUpdate, 350);
  };

  const handleYtPageDataUpdated = () => {
    checkAndUpdate();
  };

  const handlePopState = () => {
    checkAndUpdate();
  };

  window.addEventListener("yt-navigate-finish", handleYtNavigateFinish, {
    passive: true,
  });
  window.addEventListener("yt-page-data-updated", handleYtPageDataUpdated, {
    passive: true,
  });
  window.addEventListener("popstate", handlePopState, { passive: true });

  // Watch for <title> changes in case title updates asynchronously
  let titleObserver: MutationObserver | null = null;
  const titleElement = document.querySelector("title");
  if (titleElement && typeof MutationObserver !== "undefined") {
    titleObserver = new MutationObserver(() => {
      checkAndUpdate();
    });
    titleObserver.observe(titleElement, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  // Teardown function for clean resource cleanup
  return () => {
    window.removeEventListener("yt-navigate-finish", handleYtNavigateFinish);
    window.removeEventListener("yt-page-data-updated", handleYtPageDataUpdated);
    window.removeEventListener("popstate", handlePopState);
    if (titleObserver) {
      titleObserver.disconnect();
      titleObserver = null;
    }
  };
}
