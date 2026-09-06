import React, { useState } from "react";
import type { Citation } from "@youtube-ai/shared-types";
import type { ExtensionMessage } from "../types/extension";

interface CitationChipProps {
  citation: Citation;
  videoId?: string;
  className?: string;
}

export function formatTimestamp(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export const CitationChip: React.FC<CitationChipProps> = ({
  citation,
  videoId,
  className = "",
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [seekFeedback, setSeekFeedback] = useState<string | null>(null);

  const startFormatted = formatTimestamp(citation.start);
  const endFormatted = formatTimestamp(citation.end);

  const handleSeek = async (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
        const [activeTab] = await chrome.tabs.query({
          active: true,
          currentWindow: true,
        });
        if (activeTab?.id) {
          const msg: ExtensionMessage = {
            type: "SEEK_VIDEO",
            timestamp: citation.start,
          };
          chrome.tabs.sendMessage(activeTab.id, msg, () => {
            // Ignore if content script isn't responsive
          });
          setSeekFeedback("Seeked!");
          setTimeout(() => setSeekFeedback(null), 1500);
          return;
        }
      }
    } catch {
      // Graceful fallback
    }

    // Fallback: If not in active tab context, copy YouTube URL with &t=
    if (videoId) {
      const seekUrl = `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(citation.start)}s`;
      try {
        await navigator.clipboard.writeText(seekUrl);
        setSeekFeedback("Copied link!");
        setTimeout(() => setSeekFeedback(null), 1500);
      } catch {
        // Silently fail
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      handleSeek(e);
    }
  };

  const accessibleLabel = `Jump to video timestamp ${startFormatted} to ${endFormatted}`;

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={handleSeek}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        tabIndex={0}
        aria-label={accessibleLabel}
        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium transition-all duration-150 cursor-pointer select-none bg-amber-500/15 hover:bg-amber-500/25 active:bg-amber-500/35 text-amber-600 dark:text-amber-400 border border-amber-500/30 hover:border-amber-500/50 focus:outline-none focus:ring-2 focus:ring-amber-500/40 ${className}`}
      >
        <svg
          className="w-3 h-3 text-amber-600 dark:text-amber-400 shrink-0"
          fill="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path d="M8 5v14l11-7z" />
        </svg>
        <span>
          {startFormatted}–{endFormatted}
        </span>
        {seekFeedback && (
          <span className="ml-1 text-[9px] text-emerald-600 dark:text-emerald-400 font-sans font-semibold">
            {seekFeedback}
          </span>
        )}
      </button>

      {/* Verified Evidence Tooltip */}
      {showTooltip && (
        <div
          role="tooltip"
          className="absolute left-0 bottom-full mb-1.5 z-50 w-64 max-w-xs p-2.5 rounded-lg text-xs leading-relaxed shadow-xl pointer-events-none border border-zinc-200 dark:border-zinc-700/80 bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="flex items-center justify-between pb-1 mb-1.5 border-b border-zinc-100 dark:border-zinc-800 text-[10px] text-zinc-500 dark:text-zinc-400">
            <span className="font-semibold text-amber-600 dark:text-amber-400">
              Verified Transcript Segment
            </span>
            <span className="font-mono">
              {startFormatted} → {endFormatted}
            </span>
          </div>

          {(citation as { text?: string }).text ? (
            <p className="line-clamp-3 text-[11px] text-zinc-600 dark:text-zinc-300 italic font-sans">
              &ldquo;{(citation as { text?: string }).text?.trim()}&rdquo;
            </p>
          ) : (
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Click to seek player to {startFormatted}
            </p>
          )}
        </div>
      )}
    </span>
  );
};
