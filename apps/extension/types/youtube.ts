/**
 * Supported YouTube video presentation formats.
 */
export type YouTubeVideoType = "watch" | "shorts" | "embed";

/**
 * Normalized representation of an active YouTube video.
 */
export interface CurrentVideo {
  /** 11-character YouTube video ID */
  videoId: string;
  /** Video title extracted from page metadata or DOM, or null if unavailable */
  title: string | null;
  /** Full canonical or active URL */
  url: string;
  /** Video presentation category */
  type: YouTubeVideoType;
}

/**
 * Discriminated union modeling YouTube video detection state.
 * Prevents ambiguous nullable state combinations.
 */
export type VideoDetectionState =
  | { status: "loading" }
  | { status: "detected"; video: CurrentVideo }
  | { status: "unsupported" }
  | { status: "error"; message: string };
