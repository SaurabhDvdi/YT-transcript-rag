import type { YouTubeVideoType } from "../types/youtube";

/**
 * Standard YouTube video IDs are 11 base64url-compatible characters.
 */
const YOUTUBE_VIDEO_ID_REGEX = /^[a-zA-Z0-9_-]{11}$/;

/**
 * Validates whether a candidate string conforms to a structurally valid 11-character YouTube video ID.
 */
export function isValidYouTubeVideoId(id: string | null | undefined): boolean {
  if (!id || typeof id !== "string") {
    return false;
  }
  return YOUTUBE_VIDEO_ID_REGEX.test(id.trim());
}

/**
 * Validates whether a hostname belongs to legitimate YouTube domains.
 * Prevents domain spoofing (e.g., evil-youtube.com or youtube.com.attacker.com).
 */
export function isYouTubeHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return (
    normalized === "youtube.com" ||
    normalized === "www.youtube.com" ||
    normalized === "m.youtube.com" ||
    normalized === "music.youtube.com" ||
    normalized === "youtu.be"
  );
}

/**
 * Safely parses a URL string into a URL instance.
 * Returns null if the URL is malformed.
 */
function safeParseUrl(url: string): URL | null {
  if (!url || typeof url !== "string") {
    return null;
  }
  try {
    return new URL(url.trim());
  } catch {
    return null;
  }
}

/**
 * Determines whether a given URL points to an active YouTube video page
 * (standard watch page, shorts, or embed).
 */
export function isYouTubeVideoPage(url: string): boolean {
  const parsed = safeParseUrl(url);
  if (!parsed || !isYouTubeHost(parsed.hostname)) {
    return false;
  }

  const id = extractYouTubeVideoId(url);
  return id !== null && isValidYouTubeVideoId(id);
}

/**
 * Determines the YouTube video presentation format from a URL.
 * Returns "watch", "shorts", "embed", or null if not a video URL.
 */
export function extractYouTubeVideoType(url: string): YouTubeVideoType | null {
  const parsed = safeParseUrl(url);
  if (!parsed || !isYouTubeHost(parsed.hostname)) {
    return null;
  }

  const normalizedHost = parsed.hostname.toLowerCase();
  const pathname = parsed.pathname;

  // youtu.be shortlink (e.g., https://youtu.be/Gfr50f6ZBvo)
  if (normalizedHost === "youtu.be") {
    const candidateId = pathname.slice(1).split("/")[0]?.split("?")[0];
    return isValidYouTubeVideoId(candidateId) ? "watch" : null;
  }

  // Shorts (e.g., https://www.youtube.com/shorts/Gfr50f6ZBvo)
  if (pathname.startsWith("/shorts/")) {
    const candidateId = pathname.slice("/shorts/".length).split("/")[0]?.split("?")[0];
    return isValidYouTubeVideoId(candidateId) ? "shorts" : null;
  }

  // Embeds (e.g., https://www.youtube.com/embed/Gfr50f6ZBvo)
  if (pathname.startsWith("/embed/")) {
    const candidateId = pathname.slice("/embed/".length).split("/")[0]?.split("?")[0];
    return isValidYouTubeVideoId(candidateId) ? "embed" : null;
  }

  // Watch URLs (e.g., https://www.youtube.com/watch?v=Gfr50f6ZBvo)
  if (pathname === "/watch" || pathname === "/watch/") {
    const candidateId = parsed.searchParams.get("v");
    return isValidYouTubeVideoId(candidateId) ? "watch" : null;
  }

  return null;
}

/**
 * Extracts and structurally validates the YouTube video ID from a URL.
 * Returns null if the URL is not a video page or the ID is invalid/absent.
 */
export function extractYouTubeVideoId(url: string): string | null {
  const parsed = safeParseUrl(url);
  if (!parsed || !isYouTubeHost(parsed.hostname)) {
    return null;
  }

  const normalizedHost = parsed.hostname.toLowerCase();
  const pathname = parsed.pathname;

  let candidateId: string | null = null;

  // youtu.be/<id>
  if (normalizedHost === "youtu.be") {
    candidateId = pathname.slice(1).split("/")[0]?.split("?")[0] ?? null;
  }
  // /shorts/<id>
  else if (pathname.startsWith("/shorts/")) {
    candidateId = pathname.slice("/shorts/".length).split("/")[0]?.split("?")[0] ?? null;
  }
  // /embed/<id>
  else if (pathname.startsWith("/embed/")) {
    candidateId = pathname.slice("/embed/".length).split("/")[0]?.split("?")[0] ?? null;
  }
  // /watch?v=<id>
  else if (pathname === "/watch" || pathname === "/watch/") {
    candidateId = parsed.searchParams.get("v");
  }

  if (candidateId && isValidYouTubeVideoId(candidateId)) {
    return candidateId.trim();
  }

  return null;
}
