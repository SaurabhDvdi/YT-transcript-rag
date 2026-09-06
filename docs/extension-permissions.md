# Browser Extension Permissions & Compatibility Audit

## 1. Principle of Least Privilege

The YouTube AI Assistant extension requests only the minimal set of browser permissions strictly required to detect the active video, display the sidepanel, and persist preferences and authentication state locally.

---

## 2. Permission Justifications

| Permission               | Scope                 | Justification                                                                                                                                                  |
| :----------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `storage`                | Local Browser Storage | Persists user tokens (`accessToken`, `refreshToken`), anonymous session UUID (`x-session-id`), active video ID cache, and UI preferences (e.g. drawer states). |
| `sidepanel` (Chrome MV3) | Browser Sidebar       | Provides a persistent, accessible conversational sidepanel interface that coexists with video playback without obstructing the YouTube player.                 |

### 2.1 Content Script Injections

- **Match Pattern:** `*://*.youtube.com/watch*`
- **Justification:** Injected strictly on YouTube video watch pages to:
  1. Detect URL changes and video navigation in single-page application (SPA) mode.
  2. Extract caption tracks from YouTube DOM when available.
  3. Emit status notifications to the extension background service worker.
- **Excluded Patterns:** All other domains, search pages, channel pages, and non-watch URLs are excluded from script injection.

---

## 3. Cross-Browser Compatibility Matrix

| Browser             | Manifest Version | Build Target  | Compatibility Status | Notes                                           |
| :------------------ | :--------------- | :------------ | :------------------- | :---------------------------------------------- |
| **Google Chrome**   | MV3              | `chrome-mv3`  | Full Support         | Built using standard Chrome MV3 side panel API  |
| **Mozilla Firefox** | MV2              | `firefox-mv2` | Full Support         | Built using standard Firefox MV2 sidebar action |
| **Microsoft Edge**  | MV3              | `chrome-mv3`  | Full Support         | Chromium-based; side panel supported natively   |
| **Brave**           | MV3              | `chrome-mv3`  | Full Support         | Chromium-based; full extension API support      |
| **Opera**           | MV3              | `chrome-mv3`  | Full Support         | Chromium-based; side panel supported            |
| **Vivaldi**         | MV3              | `chrome-mv3`  | Full Support         | Chromium-based; web panels supported            |

---

## 4. Build Commands

- **Chrome MV3:**
  ```bash
  npm run build
  # Artifacts output to: apps/extension/.output/chrome-mv3/
  ```
- **Firefox MV2:**
  ```bash
  npm run build:firefox
  # Artifacts output to: apps/extension/.output/firefox-mv2/
  ```
