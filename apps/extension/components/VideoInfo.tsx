import React, { useState } from "react";
import type { CurrentVideo } from "../types/youtube";

interface VideoInfoProps {
  video: CurrentVideo;
  transcriptReady?: boolean;
  aiReady?: boolean;
  statusMessage?: string;
}

export const VideoInfo: React.FC<VideoInfoProps> = ({
  video,
  transcriptReady = false,
  aiReady = false,
  statusMessage,
}) => {
  const [copied, setCopied] = useState(false);
  const [thumbError, setThumbError] = useState(false);

  const thumbnailUrl = `https://i.ytimg.com/vi/${video.videoId}/hqdefault.jpg`;

  const handleCopyLink = async () => {
    try {
      const url = `https://www.youtube.com/watch?v=${video.videoId}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const formatVideoType = (type: CurrentVideo["type"]): string => {
    switch (type) {
      case "shorts":
        return "Shorts";
      case "embed":
        return "Embed";
      default:
        return "Video";
    }
  };

  return (
    <div className="rounded-xl overflow-hidden bg-white dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800 shadow-xs transition-colors">
      <div className="flex p-3 gap-3">
        {/* Thumbnail with Fallback */}
        <div className="relative w-20 h-14 rounded-lg overflow-hidden bg-zinc-200 dark:bg-zinc-800 shrink-0 border border-zinc-200 dark:border-zinc-700/60 flex items-center justify-center">
          {!thumbError ? (
            <img
              src={thumbnailUrl}
              alt={video.title || "Video thumbnail"}
              onError={() => setThumbError(true)}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-500">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M10 15l5.19-3L10 9v6m11.56-7.83c.13.47.22 1.1.28 1.9.07.8.1 1.49.1 2.09L22 12c0 2.19-.16 3.8-.44 4.83-.25.9-.83 1.48-1.73 1.73-.47.13-1.33.22-2.65.28-1.3.07-2.49.1-3.59.1L12 19c-4.19 0-6.8-.16-7.83-.44-.9-.25-1.48-.83-1.73-1.73-.13-.47-.22-1.1-.28-1.9-.07-.8-.1-1.49-.1-2.09L2 12c0-2.19.16-3.8.44-4.83.25-.9.83-1.48 1.73-1.73.47-.13 1.33-.22 2.65-.28 1.3-.07 2.49-.1 3.59-.1L12 5c4.19 0 6.8.16 7.83.44.9.25 1.48.83 1.73 1.73z" />
              </svg>
            </div>
          )}
          <span className="absolute bottom-1 right-1 px-1 py-0.2 rounded text-[9px] font-medium bg-black/75 text-white">
            {formatVideoType(video.type)}
          </span>
        </div>

        {/* Video Info & Status */}
        <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
          <div>
            <h2
              className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 leading-snug line-clamp-2"
              title={video.title ?? "YouTube Video"}
            >
              {video.title ?? "YouTube Video"}
            </h2>
          </div>

          {/* Friendly Status Badges */}
          <div className="flex items-center gap-1.5 flex-wrap pt-1 text-[10px]">
            {transcriptReady ? (
              <span className="inline-flex items-center px-1.5 py-0.2 rounded font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
                <span className="w-1.5 h-1.5 mr-1 rounded-full bg-emerald-500" />
                Transcript ✓
              </span>
            ) : (
              <span className="inline-flex items-center px-1.5 py-0.2 rounded font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/40">
                <span className="w-1.5 h-1.5 mr-1 rounded-full bg-amber-500 animate-ping" />
                Preparing video...
              </span>
            )}

            {aiReady ? (
              <span className="inline-flex items-center px-1.5 py-0.2 rounded font-medium bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/40">
                AI Ready ✓
              </span>
            ) : (
              <span className="inline-flex items-center px-1.5 py-0.2 rounded font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700/60">
                Preparing AI...
              </span>
            )}

            {/* Copy Link Button */}
            <button
              type="button"
              onClick={handleCopyLink}
              title="Copy YouTube URL"
              className="ml-auto text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 p-0.5 rounded transition-colors"
            >
              {copied ? (
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                  Copied!
                </span>
              ) : (
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {statusMessage && (
        <div className="px-3 py-1.5 bg-zinc-50 dark:bg-zinc-950/50 border-t border-zinc-100 dark:border-zinc-800/60 text-[10px] text-zinc-500 dark:text-zinc-400">
          {statusMessage}
        </div>
      )}
    </div>
  );
};
